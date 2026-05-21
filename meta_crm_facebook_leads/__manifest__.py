{
    'name': "CRM Meta Lead Ads",
    'summary': "Sync Facebook Leads with Odoo CRM",
    'description': """
        Automatically sync Facebook Lead Ads into Odoo CRM.
    """,
    'author': "Proptech",
    'website': "https://www.proptech.sa/",
    'category': 'Lead Automation',
    'version': '19.0.1.0.0',
    'depends': ['crm', 'base', 'utm'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/crm.facebook.form.mapping.csv',
        'views/crm_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
