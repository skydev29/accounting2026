# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Assets Management Odoo',
    'version': '19.0.0.0',
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': ['account'],
    'summary': 'Assets Management for Odoo Community - depreciation, journal entries, asset categories',
    'description': """
Assets Management
=================
Manage assets owned by a company or a person.
Keeps track of depreciations, and creates corresponding journal entries.
    """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.in',
    'price': 39,
    'currency': 'EUR',
    'data': [
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/asset_depreciation_confirmation_wizard_views.xml',
        'wizard/asset_modify_views.xml',
        'views/account_asset_views.xml',
        'views/account_invoice_views.xml',
        'views/product_views.xml',
        'report/account_asset_report_views.xml',
        'data/account_asset_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bi_account_asset/static/src/scss/account_asset.scss',
            'bi_account_asset/static/src/js/account_asset.js',
            'bi_account_asset/static/src/xml/account_asset_templates.xml',
        ],
    },
    'images': ['static/description/Banner.gif'],
    'live_test_url': 'https://youtu.be/VGgxj_ux9e4',
    'installable': True,
    'application': False,
}
