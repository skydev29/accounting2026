from odoo import models, api


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model
    def get_crm_facebook_config(self):
        get_param = self.sudo().get_param
        return {
            'crm_fb_app_id': get_param('meta_facebook_leads_syc.crm_fb_app_id', False),
            'crm_fb_app_secret': get_param('meta_facebook_leads_syc.crm_fb_app_secret', False),
            'crm_fb_access_token': get_param('meta_facebook_leads_syc.crm_fb_access_token', False),
            'crm_fb_api_version': get_param('meta_facebook_leads_syc.crm_fb_api_version', 'v21.0'),
        }
