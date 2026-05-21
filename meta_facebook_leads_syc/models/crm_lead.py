import json
import logging
import time
from datetime import timezone

import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_GRAPH_API_BASE = 'https://graph.facebook.com/'


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    facebook_lead_id = fields.Char(readonly=True)
    facebook_page_id = fields.Many2one(
        'crm.facebook.page', related='facebook_form_id.page_id',
        store=True, readonly=True
    )
    facebook_form_id = fields.Many2one('crm.facebook.form', readonly=True)
    facebook_adset_id = fields.Many2one('utm.adset', readonly=True)
    facebook_ad_id = fields.Many2one(
        'crm.facebook.ad', readonly=True, string='Facebook Ad'
    )
    facebook_campaign_id = fields.Many2one(
        'utm.campaign', related='campaign_id',
        store=True, readonly=True, string='Facebook Campaign'
    )
    facebook_date_create = fields.Datetime(readonly=True)
    facebook_is_organic = fields.Boolean(readonly=True)

    _facebook_lead_unique = models.Constraint(
        'unique(facebook_lead_id)',
        'This Facebook lead already exists!'
    )

    @api.model
    def _facebook_get(self, path_or_url, params=None, retries=3):
        """GET request to the Facebook Graph API with retry on transient network errors."""
        if path_or_url.startswith('http'):
            url = path_or_url
        else:
            version = self.env['ir.config_parameter'].sudo().get_param(
                'meta_facebook_leads_syc.crm_fb_api_version', 'v21.0'
            )
            url = '%s%s/%s' % (_GRAPH_API_BASE, version, path_or_url.lstrip('/'))

        last_exc = None
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=30)
                return resp.json()
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    _logger.warning(
                        'Facebook API request failed (attempt %d/%d): %s. Retrying in %ds.',
                        attempt + 1, retries, exc, wait,
                    )
                    time.sleep(wait)
        raise last_exc

    def get_ad(self, lead):
        ad_obj = self.env['crm.facebook.ad']
        if not lead.get('ad_id'):
            return False
        existing = ad_obj.search([('facebook_ad_id', '=', lead['ad_id'])], limit=1)
        if existing:
            return existing.id
        return ad_obj.create({
            'facebook_ad_id': lead['ad_id'],
            'name': lead.get('ad_name', lead['ad_id']),
        }).id

    def get_adset(self, lead):
        ad_obj = self.env['utm.adset']
        if not lead.get('adset_id'):
            return False
        existing = ad_obj.search([('facebook_adset_id', '=', lead['adset_id'])], limit=1)
        if existing:
            return existing.id
        return ad_obj.create({
            'facebook_adset_id': lead['adset_id'],
            'name': lead.get('adset_name', lead['adset_id']),
        }).id

    def get_campaign(self, lead):
        campaign_obj = self.env['utm.campaign']
        if not lead.get('campaign_id'):
            return False
        existing = campaign_obj.search(
            [('facebook_campaign_id', '=', lead['campaign_id'])], limit=1
        )
        if existing:
            return existing.id
        return campaign_obj.create({
            'facebook_campaign_id': lead['campaign_id'],
            'name': lead.get('campaign_name', lead['campaign_id']),
        }).id

    def prepare_lead_creation(self, lead, form):
        vals, notes = self.get_fields_from_data(lead, form)
        created_time = self._parse_facebook_datetime(lead.get('created_time'))
        vals.update({
            'facebook_lead_id': lead.get('id'),
            'facebook_is_organic': lead.get('is_organic', False),
            'name': self.get_opportunity_name(vals, lead, form),
            'description': '\n'.join(notes),
            'team_id': form.team_id and form.team_id.id,
            'company_id': (
                form.team_id and
                form.team_id.company_id and
                form.team_id.company_id.id or False
            ),
            'campaign_id': (
                form.campaign_id and form.campaign_id.id or
                self.get_campaign(lead)
            ),
            'source_id': form.source_id and form.source_id.id,
            'medium_id': form.medium_id and form.medium_id.id,
            'user_id': (
                form.team_id and
                form.team_id.user_id and
                form.team_id.user_id.id or False
            ),
            'facebook_ad_id': self.get_ad(lead),
            'facebook_adset_id': self.get_adset(lead),
            'facebook_form_id': form.id,
            'facebook_date_create': created_time,
        })
        return vals

    def lead_creation(self, lead, form):
        vals = self.prepare_lead_creation(lead, form)
        return self.create(vals)

    def get_opportunity_name(self, vals, lead, form):
        if vals.get('name'):
            return vals['name']
        default_name = '%s - %s' % (form.name, lead.get('id', ''))
        vals['name'] = default_name
        return default_name

    def get_fields_from_data(self, lead, form):
        vals, notes = {}, []
        mapping = {
            m.facebook_field: m.odoo_field
            for m in form.mappings.filtered(lambda m: m.odoo_field)
        }
        unmapped_fields = []
        for name, value in lead.items():
            if name in mapping:
                odoo_field = mapping[name]
                display_value = value
                if isinstance(value, list):
                    display_value = ', '.join(str(v) for v in value)
                notes.append('%s: %s' % (odoo_field.field_description, display_value))
                vals.update(self._convert_value_to_field(odoo_field, value))
            else:
                if name not in {
                    'id', 'created_time', 'ad_id', 'ad_name',
                    'adset_id', 'adset_name', 'campaign_id',
                    'campaign_name', 'is_organic', 'organic_lead'
                }:
                    unmapped_fields.append((name, value))

        for name, value in unmapped_fields:
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            notes.append('%s: %s' % (name, value))

        return vals, notes

    def process_lead_field_data(self, lead):
        field_data = lead.pop('field_data', None)
        if not field_data:
            field_data = lead.pop('answers', [])
        lead_data = dict(lead)
        normalized_data = {}
        for entry in field_data:
            name = entry.get('name')
            if not name:
                continue
            values = entry.get('values')
            if not values and entry.get('value') is not None:
                values = [entry.get('value')]
            if not values:
                continue
            normalized_data[name] = values[0]
        lead_data.update(normalized_data)
        return lead_data

    def lead_processing(self, r, form, latest_date=None):
        if not r.get('data'):
            return latest_date
        for lead in r['data']:
            lead = self.process_lead_field_data(lead)
            lead_date = self._parse_facebook_datetime(lead.get('created_time'))
            if lead_date and (not latest_date or lead_date > latest_date):
                latest_date = lead_date
            if not self.search([
                ('facebook_lead_id', '=', lead.get('id')),
                '|',
                ('active', '=', True),
                ('active', '=', False),
            ]):
                self.lead_creation(lead, form)

        try:
            self.env.cr.commit()
        except Exception:
            self.env.cr.rollback()

        if r.get('paging') and r['paging'].get('next'):
            _logger.info('Fetching a new page in Form: %s' % form.name)
            latest_date = self.lead_processing(
                self._facebook_get(r['paging']['next']), form, latest_date
            )
        return latest_date

    @api.model
    def get_facebook_leads_for_form(self, form):
        """Fetch and import leads for a single Facebook lead form."""
        field_list = (
            'created_time,field_data,answers,ad_id,ad_name,adset_id,adset_name,'
            'campaign_id,campaign_name,is_organic'
        )
        _logger.info('Fetching leads from form: %s', form.name)
        params = {
            'access_token': form.access_token,
            'fields': field_list,
            'limit': 100,
        }
        if form.date_retrieval:
            timestamp = self._get_facebook_timestamp(form.date_retrieval)
            if timestamp:
                params['filtering'] = json.dumps([{
                    'field': 'time_created',
                    'operator': 'GREATER_THAN',
                    'value': timestamp,
                }])
        r = self._facebook_get(form.facebook_form_id + '/leads', params=params)
        if r.get('error'):
            raise UserError(r['error']['message'])
        latest_date = self.lead_processing(r, form)
        if latest_date:
            form.date_retrieval = latest_date

    @api.model
    def get_facebook_leads(self):
        # Prevent concurrent cron runs using a PostgreSQL transaction-level advisory lock
        lock_id = hash('meta_facebook_leads_syc.get_facebook_leads') % (2 ** 31)
        self.env.cr.execute('SELECT pg_try_advisory_xact_lock(%s)', [lock_id])
        if not self.env.cr.fetchone()[0]:
            _logger.info('Facebook leads fetch already running, skipping.')
            return

        for form in self.env['crm.facebook.form'].search([]):
            self.get_facebook_leads_for_form(form)
        _logger.info('Fetch of leads has ended')

    @api.model
    def _convert_value_to_field(self, odoo_field, value):
        if isinstance(value, list):
            value = value[0] if value else False
        if value in (None, False, ''):
            return {odoo_field.name: False}
        if odoo_field.ttype == 'many2one':
            related_value = self.env[odoo_field.relation].search(
                [('display_name', '=', value)], limit=1
            )
            return {odoo_field.name: related_value.id if related_value else False}
        if odoo_field.ttype in ('float', 'monetary'):
            try:
                return {odoo_field.name: float(value)}
            except (ValueError, TypeError):
                return {odoo_field.name: 0.0}
        if odoo_field.ttype == 'integer':
            try:
                return {odoo_field.name: int(value)}
            except (ValueError, TypeError):
                return {odoo_field.name: 0}
        if odoo_field.ttype in ('date', 'datetime'):
            parsed_value = self._parse_facebook_datetime(value)
            return {odoo_field.name: parsed_value}
        if odoo_field.ttype == 'selection':
            return {odoo_field.name: value}
        if odoo_field.ttype == 'boolean':
            return {odoo_field.name: value == 'true' if isinstance(value, str) else bool(value)}
        return {odoo_field.name: value}

    @api.model
    def _parse_facebook_datetime(self, value):
        if not value:
            return False
        try:
            dt_value = fields.Datetime.to_datetime(value)
            return fields.Datetime.to_string(dt_value)
        except Exception:
            return value.split('+')[0].replace('T', ' ')

    @api.model
    def _get_facebook_timestamp(self, dt):
        if not dt:
            return False
        datetime_value = fields.Datetime.to_datetime(dt)
        if datetime_value.tzinfo is None:
            datetime_value = datetime_value.replace(tzinfo=timezone.utc)
        return int(datetime_value.timestamp())
