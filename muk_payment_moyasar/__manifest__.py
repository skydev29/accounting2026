# -*- coding: utf-8 -*-
# Part of MUK IT. See LICENSE file for full copyright and licensing details.
{
    'name': 'Moyasar Payment Gateway',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 1,
    'summary': 'Accept payments via Moyasar (Cards, STC Pay, Apple Pay)',
    'description': (
        'Integrates the Moyasar payment gateway into Odoo. '
        'Supports credit cards, STC Pay, and Apple Pay for e-commerce, '
        'invoicing, and portal payment flows.'
    ),
    'author': 'MUK Software',
    'website': 'https://www.muksoft.som/',
    'support': 'skymuknon@gmail.com',
    'maintainers': ['muk-smart'],
    'depends': ['base', 'website_sale', 'sale'],
    'data': [
        'views/moyasar_form.xml',
        'data/moyasar_data.xml',
        'views/payment_acquirer.xml',
        'views/payment_transaction_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'muk_payment_moyasar/static/src/scss/moyasar_form.scss',
            'muk_payment_moyasar/static/src/js/moyasar_form.js',
            'muk_payment_moyasar/static/src/interactions/payment_mixin.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 90,
    'currency': 'EUR',
    'external_dependencies': {
        'python': ['moyasar'],
    },
}
