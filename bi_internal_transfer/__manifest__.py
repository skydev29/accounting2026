# -*- coding: utf-8 -*-
{
    'name': 'Internal Transfers',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'author': 'Custom',
    'license': 'LGPL-3',
    'summary': (
        'Standalone internal transfer between cash and bank journals '
        'with automatic journal-entry creation'
    ),
    'depends': ['account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/account_internal_transfer_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
