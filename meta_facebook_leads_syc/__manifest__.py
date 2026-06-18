{
    # ─── Identity ────────────────────────────────────────────────────────────────
    'name': 'Facebook Lead Ads Sync',
    'summary': 'Sync Facebook Lead Ads directly into Odoo CRM automatically',
    'description': 'See static/description/index.html',
    'author': 'muknon',
    'maintainer': 'muknon',
    # 'website': 'https://www.odoo.com/',
    'support': 'info@skymuknon.com',

    # ─── Categorisation ──────────────────────────────────────────────────────────
    # Must match an official Odoo App Store category exactly.
    # See: https://apps.odoo.com/apps/modules/browse
    'category': 'Marketing',
    'version': '19.0.1.0.0',   # {odoo_version}.{major}.{minor}.{patch}

    # ─── Licensing & Pricing ─────────────────────────────────────────────────────
    # OPL-1  → paid / proprietary  (set price > 0)
    # LGPL-3 → free / open-source  (price = 0)
    'license': 'OPL-1',
    'price': 120.0,
    'currency': 'USD',  # 'USD' or 'EUR'

    # ─── Dependencies ────────────────────────────────────────────────────────────
    # List only direct dependencies; 'base' is always implicit.
    'depends': ['crm', 'utm'],

    # ─── App Store Assets ────────────────────────────────────────────────────────
    # static/description/icon.png      → 96×96 px PNG module icon (required)
    # static/description/banner.png    → 1200×300 px banner (shown at top of listing)
    # Additional screenshots listed below are shown in the gallery.
    'images': [
        'static/description/banner.png',
        'static/description/screenshot_01.png',
        'static/description/screenshot_02.png',
        'static/description/screenshot_03.png',
    ],

    # ─── Data Files ──────────────────────────────────────────────────────────────
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/crm.facebook.form.mapping.csv',
        'views/crm_facebook_wizard_views.xml',
        'views/crm_view.xml',
        'views/res_config_settings_views.xml',
    ],

    # ─── Flags ───────────────────────────────────────────────────────────────────
    'installable': True,
    'auto_install': False,
    'application': True,
}
