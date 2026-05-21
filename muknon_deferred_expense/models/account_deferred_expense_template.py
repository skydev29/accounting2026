# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountDeferredExpenseTemplate(models.Model):
    _name = 'muknon.deferred.expense.template'
    _description = 'Deferred Expense Template'
    _order = 'name asc'

    # ── Identity ──────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Template Name',
        required=True,
        translate=True,
    )

    # ── Accounting ────────────────────────────────────────────────────────────
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required=True,
        domain=[('type', '=', 'general')],
    )
    deferred_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Prepaid / Asset Account',
        required=True,
        help='Balance-sheet asset account that holds the prepaid amount '
             '(e.g. Prepaid Insurance, Prepaid Rent).',
    )
    expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Expense Account',
        required=True,
        help='P&L expense account to recognise into each period '
             '(e.g. Insurance Expense, Rent Expense).',
    )

    # ── Settings ──────────────────────────────────────────────────────────────
    recognition_period = fields.Selection(
        selection=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('custom', 'Custom'),
        ],
        string='Recognition Period',
        default='monthly',
        required=True,
    )
    notes = fields.Text(string='Notes')

    # ── Multi-company ─────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
