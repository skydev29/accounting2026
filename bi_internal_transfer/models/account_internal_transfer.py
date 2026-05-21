# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountInternalTransfer(models.Model):
    """
    Standalone internal-transfer record.

    Supports all four cash/bank permutations:
      Cash → Bank  |  Bank → Cash  |  Bank → Bank  |  Cash → Cash

    Workflow:  draft ──confirm──► posted ──reset──► draft
                     └──cancel──► cancelled
    """

    _name = 'account.internal.transfer'
    _description = 'Internal Transfer'
    _order = 'date desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── database-level guard (cannot be bypassed by ORM) ──────────────────────
    _sql_constraints = [
        (
            'amount_positive',
            'CHECK(amount > 0)',
            'Transfer amount must be strictly positive.',
        ),
    ]

    # ── Identity ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True,
    )

    # ── Date ──────────────────────────────────────────────────────────────────
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    # ── Transfer type ─────────────────────────────────────────────────────────
    transfer_type = fields.Selection(
        selection=[
            ('cash_to_bank', 'Cash → Bank'),
            ('bank_to_cash', 'Bank → Cash'),
            ('bank_to_bank', 'Bank → Bank'),
            ('cash_to_cash', 'Cash → Cash'),
        ],
        string='Transfer Type',
        required=True,
        tracking=True,
    )

    # Computed FA icon — used in views and reports
    transfer_icon = fields.Char(
        string='Transfer Icon',
        compute='_compute_transfer_icon',
    )

    # Computed journal type helpers — fed into view domain expressions
    journal_source_type = fields.Char(
        compute='_compute_journal_types',
        store=False,
    )
    journal_dest_type = fields.Char(
        compute='_compute_journal_types',
        store=False,
    )

    # ── Journals ──────────────────────────────────────────────────────────────
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Source Journal',
        required=True,
        ondelete='restrict',
        check_company=True,
        tracking=True,
    )
    dest_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        required=True,
        ondelete='restrict',
        check_company=True,
        tracking=True,
    )

    # ── Amount ────────────────────────────────────────────────────────────────
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        # allow the user to override the auto-computed currency when needed
        readonly=False,
    )
    memo = fields.Char(
        string='Memo / Reference',
        tracking=True,
    )

    # ── State & linked journal entry ──────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
        ondelete='set null',
    )

    # ── Company ───────────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Compute
    # ──────────────────────────────────────────────────────────────────────────

    @api.depends('transfer_type')
    def _compute_transfer_icon(self):
        _map = {
            'cash_to_bank': 'fa-university',
            'bank_to_cash': 'fa-money',
            'bank_to_bank': 'fa-exchange',
            'cash_to_cash': 'fa-inbox',
        }
        for rec in self:
            rec.transfer_icon = _map.get(rec.transfer_type, 'fa-arrows-h')

    @api.depends('transfer_type')
    def _compute_journal_types(self):
        """
        Derive the expected account.journal type for source and destination
        based on the chosen transfer scenario.

        Source:      cash  for cash_to_bank, cash_to_cash
                     bank  for bank_to_cash, bank_to_bank

        Destination: bank  for cash_to_bank, bank_to_bank
                     cash  for bank_to_cash, cash_to_cash
        """
        for rec in self:
            if rec.transfer_type in ('cash_to_bank', 'cash_to_cash'):
                rec.journal_source_type = 'cash'
            else:
                rec.journal_source_type = 'bank'

            if rec.transfer_type in ('cash_to_bank', 'bank_to_bank'):
                rec.journal_dest_type = 'bank'
            else:
                rec.journal_dest_type = 'cash'

    @api.depends(
        'journal_id',
        'journal_id.currency_id',
        'company_id',
        'company_id.currency_id',
    )
    def _compute_currency_id(self):
        """
        Use the source journal's currency when set; fall back to
        the company currency so Monetary fields always have a valid
        currency reference.
        """
        for rec in self:
            rec.currency_id = (
                rec.journal_id.currency_id
                or rec.company_id.currency_id
                or self.env.company.currency_id
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Constraints
    # ──────────────────────────────────────────────────────────────────────────

    @api.constrains('journal_id', 'dest_journal_id')
    def _check_different_journals(self):
        for rec in self:
            if (
                rec.journal_id
                and rec.dest_journal_id
                and rec.journal_id == rec.dest_journal_id
            ):
                raise ValidationError(
                    _('Source and destination journals must be different.')
                )

    # ──────────────────────────────────────────────────────────────────────────
    # Onchange
    # ──────────────────────────────────────────────────────────────────────────

    @api.onchange('transfer_type')
    def _onchange_transfer_type(self):
        """Clear journal selection whenever the transfer type changes so the
        user must explicitly pick journals that match the new type."""
        self.journal_id = False
        self.dest_journal_id = False

    # ──────────────────────────────────────────────────────────────────────────
    # ORM overrides
    # ──────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    seq.next_by_code('account.internal.transfer') or _('New')
                )
        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _(
                        'Cannot delete Internal Transfer "%s". '
                        'Only Draft transfers may be deleted.',
                        rec.name,
                    )
                )
        return super().unlink()

    # ──────────────────────────────────────────────────────────────────────────
    # Workflow
    # ──────────────────────────────────────────────────────────────────────────

    def action_confirm(self):
        """
        draft → posted

        Creates a balanced journal entry:
          CR  source-journal default account   (money leaves)
          DR  destination-journal default account   (money arrives)

        The entry is posted immediately via action_post().
        """
        self.ensure_one()

        # ── guards ────────────────────────────────────────────────────────────
        if self.amount <= 0:
            raise UserError(_('Transfer amount must be greater than zero.'))
        if self.journal_id == self.dest_journal_id:
            raise UserError(
                _('Source and destination journals must be different.')
            )
        if not self.journal_id.default_account_id:
            raise UserError(
                _(
                    'Source journal "%s" has no default account configured. '
                    'Please set one in the journal settings.',
                    self.journal_id.name,
                )
            )
        if not self.dest_journal_id.default_account_id:
            raise UserError(
                _(
                    'Destination journal "%s" has no default account configured. '
                    'Please set one in the journal settings.',
                    self.dest_journal_id.name,
                )
            )

        ref = self.memo or self.name
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': ref,
            'company_id': self.company_id.id,
            'line_ids': [
                # CREDIT — money leaves the source journal account
                (0, 0, {
                    'name': ref,
                    'account_id': self.journal_id.default_account_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'currency_id': self.currency_id.id,
                    'amount_currency': -self.amount,
                }),
                # DEBIT — money arrives at the destination journal account
                (0, 0, {
                    'name': ref,
                    'account_id': self.dest_journal_id.default_account_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'currency_id': self.currency_id.id,
                    'amount_currency': self.amount,
                }),
            ],
        })
        move.action_post()
        self.write({
            'move_id': move.id,
            'state': 'posted',
        })

    def action_reset_draft(self):
        """
        posted → draft

        Resets the linked journal entry to draft and permanently deletes it,
        then clears move_id so a new entry can be generated on next confirm.
        """
        self.ensure_one()
        if self.move_id:
            if self.move_id.state == 'posted':
                self.move_id.button_draft()
            self.move_id.unlink()
        self.write({'move_id': False, 'state': 'draft'})

    def action_cancel(self):
        """
        any → cancelled

        If a journal entry exists it is first reset to draft (so it can be
        deleted), then removed.  The transfer record itself is kept for audit
        purposes.
        """
        self.ensure_one()
        if self.move_id:
            if self.move_id.state == 'posted':
                self.move_id.button_draft()
            self.move_id.unlink()
        self.write({'move_id': False, 'state': 'cancelled'})

    # ──────────────────────────────────────────────────────────────────────────
    # Smart-button action
    # ──────────────────────────────────────────────────────────────────────────

    def action_view_move(self):
        """Open the linked journal entry in form view."""
        self.ensure_one()
        if not self.move_id:
            return {}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
            'target': 'current',
        }
