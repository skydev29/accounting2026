# -*- coding: utf-8 -*-
# Part of MUK IT. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransactionMoyasar(models.Model):
    _inherit = 'payment.transaction'

    moyasar_payment_id = fields.Char(string='Moyasar Payment ID')

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'moyasar':
            return tx

        reference = notification_data.get('reference')
        tx = self.search([
            ('reference', '=', reference),
            ('provider_code', '=', 'moyasar'),
        ])
        if not tx:
            raise ValidationError(
                "Moyasar: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process(self, provider_code, notification_data):
        super()._process(provider_code, notification_data)
        if provider_code != 'moyasar':
            return

        trans_state = notification_data.get('state')
        if not trans_state:
            return

        self.write({
            'state_message': _("Moyasar Payment Gateway Response: ") + trans_state,
        })
        if trans_state == 'done':
            self._set_done()
        elif trans_state == 'pending':
            self._set_pending()
        elif trans_state == 'cancel':
            self._set_canceled()
        else:
            _logger.warning(
                'Moyasar: unhandled transaction state %r for tx %s', trans_state, self.id
            )
            self._set_error(_("Moyasar: unhandled payment state: %s") % trans_state)

    def _extract_amount_data(self, payment_data):
        """Return amount/currency so Odoo can validate the notification."""
        if self.provider_code != 'moyasar':
            return super()._extract_amount_data(payment_data)
        return {
            'amount': payment_data.get('amount'),
            'currency_code': payment_data.get('currency'),
        }
