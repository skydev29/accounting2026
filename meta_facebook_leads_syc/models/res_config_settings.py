from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    crm_fb_app_id = fields.Char(
        'App ID',
        config_parameter='meta_facebook_leads_syc.crm_fb_app_id',
    )
    crm_fb_app_secret = fields.Char(
        'App Secret',
        config_parameter='meta_facebook_leads_syc.crm_fb_app_secret',
        password=True,
    )
    crm_fb_access_token = fields.Char(
        'Access Token',
        config_parameter='meta_facebook_leads_syc.crm_fb_access_token',
        password=True,
    )
    crm_fb_api_version = fields.Char(
        'Graph API Version',
        config_parameter='meta_facebook_leads_syc.crm_fb_api_version',
        placeholder='v21.0',
    )

    def action_open_setup_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facebook Lead Ads Setup',
            'res_model': 'crm.facebook.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }

    def action_get_access_token(self):
        redirect_url = '%s/crm_facebook_leads/auth' % (
            self.env['ir.config_parameter'].get_param('web.base.url')
        )
        auth_url = (
            'https://www.facebook.com/dialog/oauth'
            '?response_type=token'
            '&client_id={}'
            '&redirect_uri={}'
            '&scope={}'
        ).format(
            self.crm_fb_app_id,
            redirect_url,
            'leads_retrieval,pages_manage_ads,pages_read_engagement,ads_management,ads_read,pages_show_list'
        )
        return {
            'name': 'Facebook Authentication',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'current',
            'url': auth_url,
        }

    def action_get_facebook_pages(self):
        access_token = self.env['ir.config_parameter'].sudo().get_param(
            'meta_facebook_leads_syc.crm_fb_access_token'
        )
        r = self.env['crm.lead']._facebook_get(
            'me/accounts',
            params={'access_token': access_token},
        )
        if r.get('error'):
            raise ValidationError(r['error']['message'])
        if not r.get('data'):
            return
        for p in r['data']:
            if not self.env['crm.facebook.page'].search([('name', '=', p.get('id'))]):
                self.env['crm.facebook.page'].create({
                    'label': p.get('name'),
                    'name': p.get('id'),
                    'access_token': p.get('access_token'),
                })
        action = self.env.ref('meta_facebook_leads_syc.action_crm_facebook_page')
        return action.read()[0]
