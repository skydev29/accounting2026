import logging

from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CrmFacebookPage(models.Model):
    _name = 'crm.facebook.page'
    _description = 'Facebook Page'

    label = fields.Char(string='Page Label')
    name = fields.Char(required=True, string='Page ID')
    access_token = fields.Char(required=True, string='Page Access Token', password=True)
    form_ids = fields.One2many('crm.facebook.form', 'page_id', string='Lead Forms')
    form_count = fields.Integer(compute='_compute_form_count', string='Forms', store=True)

    _name_unique = models.Constraint('unique(name)', 'You cannot create a Page twice')

    def _compute_display_name(self):
        for page in self:
            page.display_name = page.label or page.name

    def _compute_form_count(self):
        for page in self:
            page.form_count = len(page.form_ids)

    def action_view_forms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead Forms',
            'res_model': 'crm.facebook.form',
            'view_mode': 'list,form',
            'domain': [('page_id', '=', self.id)],
            'context': {'default_page_id': self.id},
        }

    def form_processing(self, r):
        if not r.get('data'):
            return
        for form in r['data']:
            if self.form_ids.filtered(
                    lambda f: f.facebook_form_id == form['id']):
                continue
            if form['status'] == 'ACTIVE':
                self.env['crm.facebook.form'].create({
                    'name': form['name'],
                    'facebook_form_id': form['id'],
                    'page_id': self.id,
                }).get_fields()

        if r.get('paging') and r['paging'].get('next'):
            self.form_processing(
                self.env['crm.lead']._facebook_get(r['paging']['next'])
            )

    def get_forms(self):
        r = self.env['crm.lead']._facebook_get(
            self.name + '/leadgen_forms',
            params={'access_token': self.access_token},
        )
        if r.get('error'):
            raise ValidationError(r['error']['message'])
        self.form_processing(r)


class CrmFacebookForm(models.Model):
    _name = 'crm.facebook.form'
    _description = 'Facebook Form Page'

    name = fields.Char(required=True)
    facebook_form_id = fields.Char(required=True, string='Form ID')
    access_token = fields.Char(
        required=True, related='page_id.access_token',
        string='Page Access Token',
    )
    page_id = fields.Many2one(
        'crm.facebook.page', readonly=True,
        ondelete='cascade', string='Facebook Page'
    )
    mappings = fields.One2many('crm.facebook.form.field', 'form_id')
    team_id = fields.Many2one(
        'crm.team',
        domain=['|', ('use_leads', '=', True), ('use_opportunities', '=', True)],
        string='Sales Team'
    )
    campaign_id = fields.Many2one('utm.campaign')
    source_id = fields.Many2one('utm.source')
    medium_id = fields.Many2one('utm.medium')
    date_retrieval = fields.Datetime(string='Fetch Leads After')

    def get_fields(self):
        self.mappings.unlink()
        r = self.env['crm.lead']._facebook_get(
            self.facebook_form_id,
            params={'access_token': self.access_token, 'fields': 'questions'},
        )
        if r.get('error'):
            raise ValidationError(r['error']['message'])
        if r.get('questions'):
            for question in r.get('questions'):
                default_mapping = self.env['crm.facebook.form.mapping'].search(
                    [('facebook_field', '=', question['key'])], limit=1
                )
                self.env['crm.facebook.form.field'].create({
                    'form_id': self.id,
                    'name': question['label'],
                    'facebook_field': question['key'],
                    'odoo_field': default_mapping.odoo_field.id if default_mapping else False,
                })

    lead_count = fields.Integer(compute='_compute_lead_count', string='Leads')

    def _compute_lead_count(self):
        data = self.env['crm.lead']._read_group(
            [('facebook_form_id', 'in', self.ids)],
            groupby=['facebook_form_id'],
            aggregates=['__count'],
        )
        count_map = {form.id: cnt for form, cnt in data}
        for rec in self:
            rec.lead_count = count_map.get(rec.id, 0)

    def action_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leads — %s' % self.name,
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('facebook_form_id', '=', self.id)],
            'context': {'default_facebook_form_id': self.id},
        }

    def action_sync_leads(self):
        self.ensure_one()
        self.env['crm.lead'].get_facebook_leads_for_form(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': 'Facebook leads synced for "%s".' % self.name,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_guess_mapping(self):
        for rec in self:
            rec.mappings.action_guess_mapping()


class CrmFacebookFormField(models.Model):
    _name = 'crm.facebook.form.field'
    _description = 'Facebook form fields'

    form_id = fields.Many2one(
        'crm.facebook.form', required=True,
        ondelete='cascade', string='Form'
    )
    name = fields.Char()
    odoo_field = fields.Many2one(
        'ir.model.fields',
        domain=[
            ('model', '=', 'crm.lead'),
            ('store', '=', True),
            ('ttype', 'in', (
                'char', 'date', 'datetime', 'float', 'html',
                'integer', 'monetary', 'many2one', 'selection',
                'phone', 'text'
            ))
        ],
        ondelete='set null',
        required=False
    )
    facebook_field = fields.Char(required=True)

    _field_unique = models.Constraint(
        'unique(form_id, odoo_field, facebook_field)',
        'Mapping must be unique per form'
    )

    def action_guess_mapping(self):
        for rec in self:
            mapping = self.env['crm.facebook.form.mapping'].search(
                [('facebook_field', '=', rec.facebook_field)], limit=1
            )
            if mapping:
                rec.odoo_field = mapping.odoo_field


class CrmFacebookFormMapping(models.Model):
    _name = 'crm.facebook.form.mapping'
    _description = 'Default field mapping for new forms'

    odoo_field = fields.Many2one(
        'ir.model.fields',
        domain=[
            ('model', '=', 'crm.lead'),
            ('store', '=', True),
            ('ttype', 'in', (
                'char', 'date', 'datetime', 'float', 'html',
                'integer', 'monetary', 'many2one', 'selection',
                'phone', 'text'
            ))
        ],
        ondelete='cascade',
        required=True
    )
    facebook_field = fields.Char(required=True)

    _map_unique = models.Constraint(
        'unique(odoo_field, facebook_field)',
        'Default Mapping must be unique'
    )
