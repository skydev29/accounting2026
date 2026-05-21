# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountDeferredRevenue(models.Model):
    _name = 'account.deferred.revenue'
    _description = 'Deferred Revenue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    # ── Identity ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Name',
        required=True,
        default='New',
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # ── Links ─────────────────────────────────────────────────────────────────
    template_id = fields.Many2one(
        comodel_name='account.deferred.revenue.template',
        string='Template',
        ondelete='restrict',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        tracking=True,
    )
    invoice_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Invoice Line',
        domain="[('move_id.move_type', 'in', ['out_invoice', 'out_refund'])]",
        help='Optional link to the originating invoice line.',
    )

    # ── Amounts & dates ───────────────────────────────────────────────────────
    total_amount = fields.Monetary(
        string='Total Amount',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)

    # ── Accounting ────────────────────────────────────────────────────────────
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        domain="[('type', '=', 'general')]",
    )
    deferred_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Deferred Revenue Account',
        help='Liability / unearned income account (debited when revenue is recognised).',
    )
    recognition_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Recognition Account',
        help='Revenue account credited when income is recognised.',
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
        readonly=True,
        tracking=True,
        copy=False,
    )

    # ── Lines & moves ─────────────────────────────────────────────────────────
    line_ids = fields.One2many(
        comodel_name='account.deferred.revenue.line',
        inverse_name='deferred_id',
        string='Recognition Lines',
    )
    move_ids = fields.Many2many(
        comodel_name='account.move',
        string='Journal Entries',
        compute='_compute_move_ids',
        readonly=True,
    )
    move_count = fields.Integer(
        string='Journal Entries Count',
        compute='_compute_move_ids',
    )

    # ── Computed amounts ──────────────────────────────────────────────────────
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

    # ── Misc ──────────────────────────────────────────────────────────────────
    description = fields.Text(string='Description')

    # ──────────────────────────────────────────────────────────────────────────
    # Compute methods
    # ──────────────────────────────────────────────────────────────────────────

    @api.depends('line_ids.move_id')
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
            posted_lines = rec.line_ids.filtered(
                lambda l: l.move_id and l.move_id.state == 'posted'
            )
            rec.recognized_amount = sum(posted_lines.mapped('amount'))
            rec.remaining_amount = rec.total_amount - rec.recognized_amount

    # ──────────────────────────────────────────────────────────────────────────
    # Onchange
    # ──────────────────────────────────────────────────────────────────────────

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.journal_id = self.template_id.journal_id
            self.deferred_account_id = self.template_id.deferred_account_id
            self.recognition_account_id = self.template_id.recognition_account_id

    # ──────────────────────────────────────────────────────────────────────────
    # Constraints
    # ──────────────────────────────────────────────────────────────────────────

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise UserError(
                    _('Start Date must be earlier than or equal to End Date.')
                )

    @api.constrains('total_amount')
    def _check_total_amount(self):
        for rec in self:
            if rec.total_amount <= 0:
                raise UserError(_('Total Amount must be greater than zero.'))

    # ──────────────────────────────────────────────────────────────────────────
    # Actions / Workflow
    # ──────────────────────────────────────────────────────────────────────────

    def action_confirm(self):
        """Validate required fields, generate lines, switch to In Progress."""
        for rec in self:
            rec._check_required_fields()
            rec._generate_lines()
            rec.write({'state': 'in_progress'})

    def action_close(self):
        """Mark the record as Closed."""
        for rec in self:
            rec.write({'state': 'closed'})

    def action_reset_draft(self):
        """Delete unposted lines and revert to Draft."""
        for rec in self:
            unposted = rec.line_ids.filtered(lambda l: not l.move_id)
            unposted.unlink()
            rec.write({'state': 'draft'})

    def action_view_moves(self):
        """Smart-button action to display related journal entries."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_ids.ids)],
            'context': {'default_move_type': 'entry'},
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Business logic
    # ──────────────────────────────────────────────────────────────────────────

    def _check_required_fields(self):
        self.ensure_one()
        missing = []
        if not self.journal_id:
            missing.append(_('Journal'))
        if not self.deferred_account_id:
            missing.append(_('Deferred Revenue Account'))
        if not self.recognition_account_id:
            missing.append(_('Recognition Account'))
        if missing:
            raise UserError(
                _('Please fill in the following fields before confirming:\n%s')
                % '\n'.join('• ' + m for m in missing)
            )

    def _generate_lines(self):
        """
        Split total_amount into monthly lines between date_start and date_end
        using calendar-day proration.  The date stored on each line is the
        first day of the recognition month.
        """
        self.ensure_one()
        # Remove any previously generated lines that were not yet posted
        self.line_ids.filtered(lambda l: not l.move_id).unlink()

        date_start = self.date_start
        date_end = self.date_end
        total_days = (date_end - date_start).days + 1

        if total_days <= 0:
            return

        lines_vals = []
        # Walk month by month starting from the 1st of date_start's month
        current = date_start.replace(day=1)

        while current <= date_end:
            next_month_first = current + relativedelta(months=1)
            last_day_of_month = next_month_first - relativedelta(days=1)

            period_start = max(current, date_start)
            period_end = min(last_day_of_month, date_end)
            days_in_period = (period_end - period_start).days + 1

            amount = self.currency_id.round(
                self.total_amount * days_in_period / total_days
            )
            lines_vals.append({
                'deferred_id': self.id,
                'date': current,          # 1st of the recognition month
                'amount': amount,
            })
            current = next_month_first

        # Correct rounding drift on the last line
        if lines_vals:
            generated_total = sum(v['amount'] for v in lines_vals)
            diff = self.currency_id.round(self.total_amount - generated_total)
            if diff:
                lines_vals[-1]['amount'] = self.currency_id.round(
                    lines_vals[-1]['amount'] + diff
                )

        self.env['account.deferred.revenue.line'].create(lines_vals)

    # ──────────────────────────────────────────────────────────────────────────
    # Scheduled action
    # ──────────────────────────────────────────────────────────────────────────

    @api.model
    def _cron_post_entries(self):
        """
        Daily cron: find all pending recognition lines whose date has passed
        and post their journal entries automatically.
        """
        today = fields.Date.today()
        lines = self.env['account.deferred.revenue.line'].search([
            ('date', '<=', today),
            ('state', '=', 'pending'),
            ('deferred_id.state', '=', 'in_progress'),
        ])
        lines.action_post_entry()
