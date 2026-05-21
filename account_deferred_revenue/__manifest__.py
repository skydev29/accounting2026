{
    'name': 'Deferred Revenue',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'author': 'muknon',
    'license': 'LGPL-3',
    'summary': 'Manage deferred revenue and unearned income recognition',
    'description': 'See static/description/index.html',
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
