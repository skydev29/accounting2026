# -*- coding: utf-8 -*-
# Part of MUK IT. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class PaymentProviderMoyasar(models.Model):
    _inherit = 'payment.provider'

    def _valid_field_parameter(self, field, name):
        return name == 'domain' or super()._valid_field_parameter(field, name)

    code = fields.Selection(
        selection_add=[('moyasar', 'Moyasar')],
        ondelete={'moyasar': 'set default'},
    )
    moyasar_public_key = fields.Char(
        string='Public Key',
        required_if_provider='moyasar',
        domain="[('code', '=', 'moyasar')]",
    )
    moyasar_secret_key = fields.Char(
        string='Secret Key',
        required_if_provider='moyasar',
        domain="[('code', '=', 'moyasar')]",
    )
    apple_pay_file = fields.Binary(
        string='Apple Pay Merchant File',
        domain="[('code', '=', 'moyasar')]",
    )

    @api.constrains('apple_pay_file')
    def _create_apple_pay_attachment(self):
        """Store the Apple Pay domain-association file as an ir.attachment so it
        can be served at /.well-known/apple-developer-merchantid-domain-association."""
        for record in self:
            if not record.apple_pay_file:
                continue
            self.env['ir.attachment'].sudo().create({
                'name': 'apple-developer-merchantid-domain-association',
                'type': 'binary',
                'res_model': 'payment.provider',
                'res_id': record.id,
                'datas': record.apple_pay_file,
                'access_token': self.env['ir.attachment']._generate_access_token(),
            })

    def _should_build_inline_form(self, is_validation=False):
        """Force Moyasar to use the inline popup flow instead of a redirect."""
        if self.code == 'moyasar':
            return True
        return super()._should_build_inline_form(is_validation=is_validation)
