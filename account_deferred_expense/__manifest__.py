# -*- coding: utf-8 -*-
{
    'name': 'Deferred Expenses',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'author': 'Custom',
    'license': 'LGPL-3',
    'summary': 'Manage prepaid / deferred expenses with automatic amortisation schedules',
    'depends': ['account', 'analytic', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/account_deferred_expense_template_views.xml',
        'views/account_deferred_expense_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
