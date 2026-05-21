# -*- coding: utf-8 -*-
import calendar
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountDeferredExpense(models.Model):
    _name = 'account.deferred.expense'
    _description = 'Deferred Expense'
    _order = 'date_start desc, name'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'analytic.mixin']

    # ── Identity ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reference',
        required=True,
        default=lambda self: _('New'),
        tracking=True,
        copy=False,
    )
    description = fields.Text(string='Description')

    # ── Relations ─────────────────────────────────────────────────────────────
    template_id = fields.Many2one(
        comodel_name='account.deferred.expense.template',
        string='Template',
        ondelete='set null',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        tracking=True,
    )
    bill_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Vendor Bill Line',
        copy=False,
        help='Optional link to the originating vendor bill line.',
    )

    # ── Amounts & dates ───────────────────────────────────────────────────────
    total_amount = fields.Monetary(
        string='Total Amount',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
    )

    # ── Accounting ────────────────────────────────────────────────────────────
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        domain=[('type', '=', 'general')],
        tracking=True,
    )
    deferred_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Prepaid / Asset Account',
        tracking=True,
    )
    expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Expense Account',
        tracking=True,
    )
    # analytic_distribution + analytic_precision are provided by analytic.mixin

    # ── Lines ─────────────────────────────────────────────────────────────────
    line_ids = fields.One2many(
        comodel_name='account.deferred.expense.line',
        inverse_name='deferred_id',
        string='Recognition Schedule',
        copy=False,
    )

    # ── Computed: journal entries ─────────────────────────────────────────────
    move_ids = fields.Many2many(
        comodel_name='account.move',
        string='Journal Entries',
        compute='_compute_move_ids',
        store=False,
    )
    move_count = fields.Integer(
        string='Journal Entries Count',
        compute='_compute_move_ids',
    )

    # ── Computed: amounts ─────────────────────────────────────────────────────
    recognized_amount = fields.Monetary(
        string='Recognized Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    remaining_amount = fields.Monetary(
        string='Remaining Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )

    # ── Currency / company ────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Constraints
    # ──────────────────────────────────────────────────────────────────────────

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end <= rec.date_start:
                raise ValidationError(
                    _('End Date must be after Start Date.')
                )

    @api.constrains('total_amount')
    def _check_total_amount(self):
        for rec in self:
            if rec.total_amount <= 0:
                raise ValidationError(
                    _('Total Amount must be greater than zero.')
                )

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _('You can only delete a deferred expense in Draft state. '
                      '"%s" is in state "%s".') % (rec.name, rec.state)
                )
        return super().unlink()

    # ──────────────────────────────────────────────────────────────────────────
    # Compute
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_move_ids(self):
        for rec in self:
            moves = rec.line_ids.mapped('move_id').filtered(bool)
            rec.move_ids = moves
            rec.move_count = len(moves)

    @api.depends(
        'line_ids.amount',
        'line_ids.move_id',
        'line_ids.move_id.state',
        'total_amount',
    )
    def _compute_amounts(self):
        for rec in self:
            recognized = sum(
                line.amount
                for line in rec.line_ids
                if line.move_id and line.move_id.state == 'posted'
            )
            rec.recognized_amount = recognized
            rec.remaining_amount = rec.total_amount - recognized

    # ──────────────────────────────────────────────────────────────────────────
    # Onchange
    # ──────────────────────────────────────────────────────────────────────────

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.journal_id = self.template_id.journal_id
            self.deferred_account_id = self.template_id.deferred_account_id
            self.expense_account_id = self.template_id.expense_account_id

    # ──────────────────────────────────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────────────────────────────────

    def action_confirm(self):
        """Validate required fields, generate recognition lines, move to in_progress."""
        self.ensure_one()
        self._check_required_fields()
        self._generate_lines()
        self.state = 'in_progress'
        line_count = len(self.line_ids)
        self.message_post(
            body=_(
                'Deferred expense confirmed. %d recognition line(s) generated '
                'from %s to %s.',
                line_count,
                self.date_start.strftime('%d/%m/%Y'),
                self.date_end.strftime('%d/%m/%Y'),
            )
        )

    def action_close(self):
        """Mark record as closed."""
        self.ensure_one()
        self.state = 'closed'

    def action_reset_draft(self):
        """Delete unposted lines and move back to draft."""
        self.ensure_one()
        unposted = self.line_ids.filtered(lambda l: not l.move_id)
        unposted.unlink()
        self.state = 'draft'

    def action_view_moves(self):
        """Open journal entries related to this deferred expense."""
        self.ensure_one()
        move_ids = self.line_ids.mapped('move_id').filtered(bool).ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'context': {'create': False},
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _check_required_fields(self):
        if not self.journal_id:
            raise UserError(_('Please set a Journal before confirming.'))
        if not self.deferred_account_id:
            raise UserError(_('Please set the Prepaid / Asset Account before confirming.'))
        if not self.expense_account_id:
            raise UserError(_('Please set the Expense Account before confirming.'))

    def _generate_lines(self):
        """
        Build calendar-month recognition lines with pro-rata day-count
        for partial first/last months.  All lines are dated on the last
        day of their respective month.  The last line absorbs rounding.
        """
        # Remove any previous unposted lines
        self.line_ids.filtered(lambda l: not l.move_id).unlink()

        date_start = self.date_start
        date_end = self.date_end
        total = self.total_amount

        # Total calendar days in the span (inclusive)
        total_days = (date_end - date_start).days + 1

        # Build list of (period_start, period_end) month slices
        segments = []
        cursor = date_start
        while cursor <= date_end:
            month_last = cursor.replace(
                day=calendar.monthrange(cursor.year, cursor.month)[1]
            )
            seg_end = min(month_last, date_end)
            segments.append((cursor, seg_end))
            cursor = month_last + relativedelta(days=1)

        line_vals = []
        cumulative = 0.0
        for idx, (seg_start, seg_end) in enumerate(segments):
            days = (seg_end - seg_start).days + 1
            is_last = (idx == len(segments) - 1)
            if is_last:
                amount = round(total - cumulative, 2)
            else:
                amount = round(total * days / total_days, 2)
            cumulative += amount
            # Recognition date: last day of the month for this segment
            month_last_day = seg_end.replace(
                day=calendar.monthrange(seg_end.year, seg_end.month)[1]
            )
            line_vals.append({
                'deferred_id': self.id,
                'date': month_last_day,
                'amount': amount,
            })

        self.env['account.deferred.expense.line'].create(line_vals)

    # ──────────────────────────────────────────────────────────────────────────
    # Scheduled action
    # ──────────────────────────────────────────────────────────────────────────

    @api.model
    def _cron_post_entries(self):
        """
        Daily cron: find all pending recognition lines whose date has
        arrived, post them and log a chatter message on the parent record.
        """
        today = fields.Date.today()
        pending_lines = self.env['account.deferred.expense.line'].search([
            ('deferred_id.state', '=', 'in_progress'),
            ('date', '<=', today),
            ('move_id', '=', False),
        ])
        # Group by parent to produce a single chatter message per record
        deferred_map = {}
        for line in pending_lines:
            deferred_map.setdefault(line.deferred_id, []).append(line)

        for deferred, lines in deferred_map.items():
            for line in lines:
                line.action_post_entry()
            amounts = ', '.join(
                '%s on %s' % (
                    deferred.currency_id.symbol + '{:,.2f}'.format(l.amount),
                    l.date.strftime('%d/%m/%Y'),
                )
                for l in lines
            )
            deferred.message_post(
                body=_(
                    'Automatic recognition: %d journal entry/entries posted. %s',
                    len(lines),
                    amounts,
                )
            )
