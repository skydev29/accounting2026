import logging
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

_SCOPE = 'leads_retrieval,pages_manage_ads,pages_read_engagement,ads_management,ads_read,pages_show_list'
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

        # Verify who the token belongs to
        me = self.env['crm.lead']._facebook_get(
            'me', params={'access_token': self.access_token, 'fields': 'id,name'}
        )
        _logger.info('Facebook import pages: token owner => %s', me)

        _logger.info('Facebook import pages: calling me/accounts')
        r = self.env['crm.lead']._facebook_get(
            'me/accounts',
            params={
                'access_token': self.access_token,
                'fields': 'id,name,access_token,category',
            }
        )
        _logger.info('Facebook import pages: me/accounts response => %s', r)

        if r.get('error'):
            # A Page Token cannot call me/accounts — skip to page-token fallback
            if 'accounts' in r['error'].get('message', ''):
                _logger.info('Facebook import pages: me/accounts unsupported for this token (likely a Page Token), skipping')
            else:
                _logger.error('Facebook import pages: API error => %s', r['error'])
                raise ValidationError(r['error']['message'])

        pages = r.get('data', [])
        _logger.info('Facebook import pages: %d page(s) from me/accounts', len(pages))

        # Fallback 1: pages owned by a Business Manager account
        if not pages:
            _logger.info('Facebook import pages: me/accounts empty, trying me/businesses')
            biz_r = self.env['crm.lead']._facebook_get(
                'me/businesses',
                params={'access_token': self.access_token, 'fields': 'id,name'},
            )
            _logger.info('Facebook import pages: me/businesses response => %s', biz_r)
            for biz in biz_r.get('data', []):
                biz_id = biz.get('id')
                _logger.info('Facebook import pages: fetching owned_pages for business %s (%s)', biz.get('name'), biz_id)
                owned_r = self.env['crm.lead']._facebook_get(
                    '%s/owned_pages' % biz_id,
                    params={
                        'access_token': self.access_token,
                        'fields': 'id,name,access_token',
                    },
                )
                _logger.info('Facebook import pages: owned_pages response => %s', owned_r)
                pages.extend(owned_r.get('data', []))

        # Fallback 2: the token itself is a Page Access Token
        # When me/accounts is empty and me/businesses fails, check if the token
        # owner (from /me) is a Page by probing its leadgen_forms endpoint.
        if not pages and me.get('id') and not me.get('error'):
            _logger.info('Facebook import pages: probing token owner %s as a Page', me['id'])
            probe = self.env['crm.lead']._facebook_get(
                '%s/leadgen_forms' % me['id'],
                params={'access_token': self.access_token, 'limit': '1'},
            )
            _logger.info('Facebook import pages: leadgen_forms probe => %s', probe)
            if not probe.get('error'):
                _logger.info('Facebook import pages: token is a Page Token — using token owner as page')
                pages = [{'id': me['id'], 'name': me['name'], 'access_token': self.access_token}]

        if not pages:
            raise ValidationError(
                'No Facebook Pages could be found for this token.\n\n'
                'This usually means the token belongs to a Facebook user account '
                'that is not an admin of any Facebook Page.\n\n'
                'To fix this:\n'
                '1. Open Meta Graph API Explorer\n'
                '2. Change "User or Page" from "User Token" to your Facebook Page\n'
                '3. Generate a Page Access Token\n'
                '4. Go to CRM → Configuration → Facebook Pages → New\n'
                '5. Enter your Page ID and paste the Page Access Token\n'
                '6. Save and click "Sync Lead Forms"'
            )

        new_count = 0
        for page in pages:
            page_id = page.get('id')
            page_name = page.get('name')
            if self.env['crm.facebook.page'].search([('name', '=', page_id)], limit=1):
                _logger.info('Facebook import pages: skipping existing page %s (%s)', page_name, page_id)
                continue
            self.env['crm.facebook.page'].create({
                'label': page_name,
                'name': page_id,
                'access_token': page.get('access_token'),
            })
            _logger.info('Facebook import pages: created page %s (%s)', page_name, page_id)
            new_count += 1

        _logger.info('Facebook import pages: done — %d new page(s) imported', new_count)
        self.write({'step': 4, 'pages_imported': new_count})
        return self._reopen()

    # ── Step 4 action ──────────────────────────────────────────────────────────

    def action_go_to_pages(self):
        return self.env.ref('meta_facebook_leads_syc.action_crm_facebook_page').read()[0]
