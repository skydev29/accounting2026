/** @odoo-module */

import { PaymentForm } from '@payment/interactions/payment_form';
import { rpc } from '@web/core/network/rpc';
import { patch } from '@web/core/utils/patch';

patch(PaymentForm.prototype, {
    async _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'moyasar') {
            return await super._processRedirectFlow(
                providerCode, paymentOptionId, paymentMethodCode, processingValues
            );
        }
        await this._processMoyasarPaymentData();
        $('#moyasarpayment').modal('show');
        $('#wrapwrap').css('z-index', 1051);
    },

    async _processMoyasarPaymentData() {
        let portal_order = {};
        const urlParams = new URLSearchParams(window.location.search);

        if (urlParams.get('sale_order_id')) {
            portal_order = { generate_link_sale_order: urlParams.get('sale_order_id') };
        } else if (urlParams.get('invoice_id')) {
            portal_order = { generate_link_invoice: urlParams.get('invoice_id') };
        } else if (document.getElementById('portal_order_id')?.value) {
            portal_order = { portal_order: document.getElementById('portal_order_id').value };
        } else if (document.getElementById('portal_invoice_id')?.value) {
            portal_order = { portal_invoice_order: document.getElementById('portal_invoice_id').value };
        } else if (document.getElementById('pos_order_id')?.value) {
            portal_order = { pos_order: document.getElementById('pos_order_id').value };
        }

        const data = await rpc('/get/moyasar/order', { data: true, portal_order });

        if (!data || data.success === false) {
            console.warn('Moyasar: could not resolve order/invoice config.');
            return;
        }

        // Convert amount to the smallest currency unit required by the Moyasar API
        let amount = data.amount;
        switch (data.currency) {
            case 'SAR':
            case 'USD':
                amount *= 100;
                break;
            case 'KWD':
                amount *= 1000;
                break;
            case 'JPY':
                // no conversion — JPY has no sub-unit
                break;
            default:
                amount *= 100;
        }

        Moyasar.init({
            element: '.mysr-form',
            amount: amount.toFixed(),
            currency: data.currency,
            description: String(data.description || ''),
            publishable_api_key: data.public_key,
            callback_url: `${data.callback_url}/payment-status-return`,
            methods: ['creditcard', 'stcpay', 'applepay'],
            apple_pay: {
                country: 'SA',
                label: 'MUK Payment',
                supported_countries: ['SA', 'US'],
                validate_merchant_url: 'https://api.moyasar.com/v1/applepay/initiate',
                validation_url: 'https://apple-pay-gateway.apple.com/paymentservices/paymentSession',
            },
        });
    },
});
