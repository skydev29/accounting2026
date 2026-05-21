# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Analytic Accounts Budgets Management Odoo',
    'category': 'Accounting',
    'version': '19.0.0.1.0',
    'summary': 'Account Budget Management with Analytic Accounts - Community Edition',
    'description': """
This module allows accountants to manage analytic and crossovered budgets.
==========================================================================

Once the Budgets are defined (in Invoicing/Budgets/Budgets), the Project Managers
can set the planned amount on each Analytic Account.
""",
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    'depends': ['account', 'project', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'security/account_budget_security.xml',
        'views/account_analytic_account_views.xml',
        'views/account_budget_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'demo': ['data/account_budget_demo.xml'],
    'images': ['static/description/Banner.png'],
    'license': 'LGPL-3',
}
