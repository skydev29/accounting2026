import requests
from odoo import fields, models, api
from odoo.exceptions import ValidationError

GRAPH_API = 'https://graph.facebook.com/v17.0/'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    crm_fb_app_id = fields.Char(
        'App ID',
        config_parameter='meta_crm_facebook_leads.crm_fb_app_id'
    )
    crm_fb_app_secret = fields.Char(
        'App Secret',
        config_parameter='meta_crm_facebook_leads.crm_fb_app_secret'
    )
    crm_fb_access_token = fields.Char(
        'Access Token',
        config_parameter='meta_crm_facebook_leads.crm_fb_access_token'
    )

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
            'leads_retrieval,pages_manage_ads,pages_read_engagement,ads_management'
        )
        return {
            'name': 'Facebook Authentication',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'current',
            'url': auth_url,
        }

    def action_get_facebook_pages(self):
        r = requests.get(
            GRAPH_API + 'me/accounts',
            params={'access_token': self.crm_fb_access_token}
        ).json()
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
        action = self.env.ref('meta_crm_facebook_leads.action_crm_facebook_page')
        return action.read()[0]
