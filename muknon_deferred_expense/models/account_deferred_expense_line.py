# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountDeferredExpenseLine(models.Model):
    _name = 'muknon.deferred.expense.line'
    _description = 'Deferred Expense Line'
    _order = 'date asc'

    # ── Relations ─────────────────────────────────────────────────────────────
    deferred_id = fields.Many2one(
        comodel_name='muknon.deferred.expense',
        string='Deferred Expense',
        required=True,
        ondelete='cascade',
        index=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
        ondelete='set null',
    )

    # ── Amounts & date ────────────────────────────────────────────────────────
    date = fields.Date(string='Date', required=True)
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='deferred_id.currency_id',
        store=True,
        readonly=True,
    )

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('posted', 'Posted'),
        ],
        string='Status',
        compute='_compute_state',
        store=True,
    )
    parent_state = fields.Selection(
        related='deferred_id.state',
        string='Parent Status',
        store=False,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Compute
    # ──────────────────────────────────────────────────────────────────────────

    @api.depends('move_id', 'move_id.state')
    def _compute_state(self):
        for line in self:
            if line.move_id and line.move_id.state == 'posted':
                line.state = 'posted'
            else:
                line.state = 'pending'

    # ──────────────────────────────────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────────────────────────────────

    def action_post_entry(self):
        """
        Create and post a journal entry that recognises one period of expense:
          DR  expense_account_id   (recognise the expense in P&L)
          CR  deferred_account_id  (reduce the prepaid/asset balance)
        """
        for line in self:
            if line.state == 'posted':
                raise UserError(
                    _('Recognition line dated %s is already posted.')
                    % line.date.strftime('%d/%m/%Y')
                )
            deferred = line.deferred_id

            if not deferred.journal_id:
                raise UserError(
                    _('No journal defined on deferred expense "%s".') % deferred.name
                )
            if not deferred.expense_account_id or not deferred.deferred_account_id:
                raise UserError(
                    _('Expense or prepaid account is missing on "%s".') % deferred.name
                )

            move_vals = {
                'move_type': 'entry',
                'date': line.date,
                'journal_id': deferred.journal_id.id,
                'ref': deferred.name,
                'company_id': deferred.company_id.id,
                'line_ids': [
                    # DR – expense account (recognise the cost)
                    (0, 0, {
                        'name': deferred.name,
                        'account_id': deferred.expense_account_id.id,
                        'debit': line.amount,
                        'credit': 0.0,
                        'currency_id': deferred.currency_id.id,
                        'analytic_distribution': deferred.analytic_distribution or False,
                    }),
                    # CR – prepaid/asset account (reduce the asset)
                    (0, 0, {
                        'name': deferred.name,
                        'account_id': deferred.deferred_account_id.id,
                        'debit': 0.0,
                        'credit': line.amount,
                        'currency_id': deferred.currency_id.id,
                    }),
                ],
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            line.move_id = move
