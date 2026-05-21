# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountDeferredRevenueTemplate(models.Model):
    _name = 'muknon.deferred.revenue.template'
    _description = 'Deferred Revenue Template'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        domain=[('type', '=', 'general')],
        required=True,
    )
    deferred_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Deferred Revenue Account',
        required=True,
        help='Liability account for unearned income (e.g. Deferred Revenue).',
    )
    recognition_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Recognition Account',
        required=True,
        help='Revenue account credited when income is recognised.',
    )
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
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
