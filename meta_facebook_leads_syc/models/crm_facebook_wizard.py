import logging
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

_SCOPE = 'leads_retrieval,pages_manage_ads,pages_read_engagement,ads_management'
_PARAM = 'meta_facebook_leads_syc.crm_fb_%s'


class CrmFacebookSetupWizard(models.TransientModel):
    _name = 'crm.facebook.setup.wizard'
    _description = 'Facebook Lead Ads Setup Wizard'

    step = fields.Integer(default=1)

    # Step 1 — connection method
    method = fields.Selection([
        ('own', 'My own Facebook App'),
        ('shared', 'Shared connector'),
    ], default='own', required=True, string='Connection Method')
    app_id = fields.Char('App ID')
    app_secret = fields.Char('App Secret')
    api_version = fields.Char('API Version', default='v21.0')

    # Step 2 — token
    access_token = fields.Char('Access Token')

    # Step 4 — summary (readonly)
    pages_imported = fields.Integer('New Pages Added', readonly=True)

    # ── Defaults ──────────────────────────────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        p = self.env['ir.config_parameter'].sudo()
        app_id = p.get_param(_PARAM % 'app_id', '')
        token = p.get_param(_PARAM % 'access_token', '')
        vals.update({
            'app_id': app_id,
            'app_secret': p.get_param(_PARAM % 'app_secret', ''),
            'access_token': token,
            'api_version': p.get_param(_PARAM % 'api_version', 'v21.0'),
            # Skip to step 2 if credentials already set but token missing
            'step': 2 if app_id and not token else 1,
        })
        return vals

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }

    def _oauth_url(self, app_id):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        redirect = '%s/crm_facebook_leads/auth' % base
        return (
            'https://www.facebook.com/dialog/oauth'
            '?response_type=token&client_id=%s&redirect_uri=%s&scope=%s'
        ) % (app_id, redirect, _SCOPE)

    def _save_step1(self):
        p = self.env['ir.config_parameter'].sudo()
        p.set_param(_PARAM % 'app_id', self.app_id or '')
        p.set_param(_PARAM % 'app_secret', self.app_secret or '')
        p.set_param(_PARAM % 'api_version', self.api_version or 'v21.0')

    # ── Step 1 actions ─────────────────────────────────────────────────────────

    def action_authorize_own(self):
        self.ensure_one()
        if not self.app_id:
            raise UserError('Enter your App ID before authorising.')
        self._save_step1()
        return {'type': 'ir.actions.act_url', 'url': self._oauth_url(self.app_id), 'target': 'new'}

    def action_authorize_shared(self):
        self.ensure_one()
        shared_id = self.env['ir.config_parameter'].sudo().get_param(
            _PARAM % 'shared_app_id', ''
        )
        if not shared_id:
            raise UserError(
                'The shared connector is not configured.\n'
                'Ask your administrator to set the system parameter:\n'
                '"meta_facebook_leads_syc.crm_fb_shared_app_id".'
            )
        return {'type': 'ir.actions.act_url', 'url': self._oauth_url(shared_id), 'target': 'new'}

    # ── Navigation ─────────────────────────────────────────────────────────────

    def action_next(self):
        self.ensure_one()
        if self.step == 1:
            self._save_step1()
        elif self.step == 2:
            if not self.access_token:
                raise UserError('Paste your Access Token before continuing.')
            self.env['ir.config_parameter'].sudo().set_param(
                _PARAM % 'access_token', self.access_token
            )
        self.write({'step': self.step + 1})
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        self.write({'step': self.step - 1})
        return self._reopen()

    # ── Step 3 action ──────────────────────────────────────────────────────────

    def action_import_pages(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError('Access Token is required to import pages.')

        r = self.env['crm.lead']._facebook_get(
            'me/accounts', params={'access_token': self.access_token}
        )
        if r.get('error'):
            raise ValidationError(r['error']['message'])

        new_count = 0
        for page in r.get('data', []):
            if self.env['crm.facebook.page'].search(
                [('name', '=', page.get('id'))], limit=1
            ):
                continue
            self.env['crm.facebook.page'].create({
                'label': page.get('name'),
                'name': page.get('id'),
                'access_token': page.get('access_token'),
            })
            new_count += 1

        self.write({'step': 4, 'pages_imported': new_count})
        return self._reopen()

    # ── Step 4 action ──────────────────────────────────────────────────────────

    def action_go_to_pages(self):
        return self.env.ref('meta_facebook_leads_syc.action_crm_facebook_page').read()[0]
