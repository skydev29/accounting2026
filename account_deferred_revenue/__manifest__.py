{
    'name': 'Deferred Revenue',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Manage deferred revenue and unearned income recognition',
    'description': """
Deferred Revenue
================
This module adds deferred revenue (unearned income) management to Odoo Accounting.

Features:
- Define reusable deferred revenue templates (journal, accounts, period)
- Create deferred revenue records linked to invoices or partners
- Automatically generate monthly recognition lines with pro-rata proration
- Post journal entries manually or via a daily scheduled action
- Track recognized vs. remaining amounts in real-time
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/account_deferred_revenue_template_views.xml',
        'views/account_deferred_revenue_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
