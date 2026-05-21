# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    partial_budget_approve = fields.Boolean(
        string='Partial Budget Approve',
        config_parameter='bi_account_budget.partial_budget_approve',
    )
