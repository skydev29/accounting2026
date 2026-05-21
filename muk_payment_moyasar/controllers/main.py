# -*- coding: utf-8 -*-
# Part of MUK IT. See LICENSE file for full copyright and licensing details.

import logging

import moyasar

from odoo import http
from odoo.http import content_disposition, request

_logger = logging.getLogger(__name__)


class MoyasarPaymentController(http.Controller):

    # ─────────────────────────────────────────────────────────────────────────
    # Apple Pay domain-association file
    # ─────────────────────────────────────────────────────────────────────────

    @http.route(
        ['/.well-known/apple-developer-merchantid-domain-association'],
        type='http', auth='public', website=True, sitemap=False,
    )
    def applepay_merchant_file(self, **post):
        ir_attach = request.env['ir.attachment'].sudo().search(
            [('res_model', '=', 'payment.provider')], order='id desc', limit=1
        )
        return request.make_response(
            ir_attach.raw.decode('ascii'),
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition',
                 content_disposition('apple-developer-merchantid-domain-association')),
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Payment callback
    # ─────────────────────────────────────────────────────────────────────────

    @http.route(
        ['/payment-status-return'],
        type='http', auth='public', website=True, sitemap=False, csrf=False,
    )
    def get_moyasar_payment_status(self, **post):
        """
        Moyasar payment callback.

        Supports two flows:
          A) SaaS direct-invoice   — payment URL contains &invoice_id=N
          B) Classic sale.order    — description matches an order name,
                                     or session carries sale_order_id
        """
        status = post.get('status')
        payment_id = post.get('id')

        # Fetch the full payment object from Moyasar
        provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'moyasar')], limit=1
        )
        moyasar.api_key = provider.moyasar_secret_key
        payment = moyasar.Payment.fetch(str(payment_id))
        _logger.info('Moyasar callback — payment_id=%s status=%s', payment_id, status)

        invoice, latest_tx = self._resolve_invoice_and_tx(post, payment)

        if not invoice:
            _logger.error(
                'Moyasar callback: could not resolve invoice for payment_id=%s', payment_id
            )
            return request.redirect('/payment/status')

        if not latest_tx:
            _logger.warning(
                'No transaction linked to invoice %s — will update invoice directly',
                invoice.id,
            )

        if status == 'paid':
            return self._handle_paid(payment_id, invoice, latest_tx)
        return self._handle_failed(payment_id, payment, invoice, latest_tx)

    # ─────────────────────────────────────────────────────────────────────────
    # Resolution helper
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_invoice_and_tx(self, post, payment):
        """
        Return (invoice: account.move, latest_tx: payment.transaction | None).

        Resolution priority:
          1. invoice_id URL param         → direct SaaS invoice (numeric ID)
          2. description starts with INV/ → SaaS invoice looked up by name
          3. description matches SO name  → classic sale.order flow
          4. session sale_order_id        → website cart fallback
        """
        description = getattr(payment, 'description', None) or ''
        _logger.info('Moyasar _resolve_invoice_and_tx — description=%s', description)

        # Path 1: numeric invoice_id in callback URL
        invoice_id_param = post.get('invoice_id')
        if invoice_id_param:
            try:
                inv = request.env['account.move'].sudo().browse(int(invoice_id_param))
                if inv.exists():
                    latest_tx = self._latest_tx_on_invoice(inv)
                    _logger.info('Path 1 — invoice_id param: invoice=%s tx=%s',
                                 inv.id, latest_tx and latest_tx.id)
                    return inv, latest_tx
            except Exception as exc:
                _logger.warning('Path 1 failed: %s', exc)

        # Path 2: description is an invoice reference (INV/… or RINV/…)
        if description and (description.startswith('INV/') or description.startswith('RINV/')):
            inv = request.env['account.move'].sudo().search(
                [('name', '=', description), ('move_type', '=', 'out_invoice')], limit=1
            )
            if inv.exists():
                latest_tx = self._latest_tx_on_invoice(inv)
                _logger.info('Path 2 — invoice by name: invoice=%s tx=%s',
                             inv.id, latest_tx and latest_tx.id)
                return inv, latest_tx
            _logger.warning('Path 2 — invoice name %s not found', description)

        # Path 3: description matches a sale.order name
        if description:
            order = request.env['sale.order'].sudo().search(
                [('name', '=', description)], limit=1
            )
            if order.exists():
                if not order.invoice_ids and order.state == 'sale':
                    try:
                        order._create_invoices()
                        order.invalidate_recordset()
                    except Exception as exc:
                        _logger.warning('Could not auto-create invoice for order %s: %s',
                                        order.name, exc)
                if order.invoice_ids:
                    inv = order.invoice_ids.sorted('id', reverse=True)[0]
                    latest_tx = (self._latest_tx_on_invoice(inv)
                                 or self._latest_tx_on_order(order))
                    _logger.info('Path 3 — sale order: order=%s invoice=%s tx=%s',
                                 order.name, inv.id, latest_tx and latest_tx.id)
                    return inv, latest_tx

        # Path 4: session sale_order_id (website cart)
        sale_order_id = request.session.get('sale_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            if order.exists() and order.invoice_ids:
                inv = order.invoice_ids.sorted('id', reverse=True)[0]
                latest_tx = (self._latest_tx_on_invoice(inv)
                             or self._latest_tx_on_order(order))
                _logger.info('Path 4 — session order: order=%s invoice=%s tx=%s',
                             order.name, inv.id, latest_tx and latest_tx.id)
                return inv, latest_tx

        _logger.error('All resolution paths failed — payment_id=%s description=%s',
                      post.get('id'), description)
        return None, None

    # ─────────────────────────────────────────────────────────────────────────
    # Payment outcome handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_paid(self, payment_id, invoice, latest_tx):
        """Mark the payment as successful and post the invoice."""
        if latest_tx:
            data = {
                'state': 'done',
                'reference': latest_tx.reference,
                'amount': invoice.amount_total,
                'amount_data': {
                    'amount': invoice.amount_total,
                    'currency': invoice.currency_id.name,
                },
                'currency': invoice.currency_id.name,
                'moyasar_payment_id': payment_id,
            }
            try:
                latest_tx.sudo()._process('moyasar', data)
                latest_tx.write({'moyasar_payment_id': payment_id})
                _logger.info('Transaction %s processed as done', latest_tx.id)
            except Exception as exc:
                _logger.error('Error processing paid transaction %s: %s', latest_tx.id, exc)
                try:
                    latest_tx.write({'moyasar_payment_id': payment_id, 'state': 'done'})
                    latest_tx._set_done()
                except Exception:
                    pass
        else:
            _logger.info(
                'No transaction for invoice %s — marking invoice paid directly', invoice.id
            )

        # Post the invoice if still in draft
        if invoice.state == 'draft':
            try:
                invoice.action_post()
                _logger.info('Invoice %s posted after successful payment', invoice.id)
            except Exception as exc:
                _logger.warning('Could not post invoice %s: %s', invoice.id, exc)

        # Register payment directly when no transaction is linked
        if not latest_tx and invoice.state == 'posted' and invoice.payment_state != 'paid':
            try:
                journal = request.env['account.journal'].sudo().search(
                    [('type', '=', 'bank'),
                     ('company_id', '=', invoice.company_id.id)],
                    limit=1,
                )
                if journal:
                    invoice.with_context(
                        default_journal_id=journal.id
                    ).action_register_payment()
                    _logger.info('Direct payment registered on invoice %s', invoice.id)
            except Exception as exc:
                _logger.warning('Could not auto-register payment on invoice %s: %s',
                                invoice.id, exc)

        return request.redirect('/payment/status')

    def _handle_failed(self, payment_id, payment, invoice, latest_tx):
        """Mark the payment as cancelled and render an error page."""
        try:
            error_message = (
                payment.source.get('message')
                if isinstance(payment.source, dict)
                else payment.source.message
            )
        except Exception:
            error_message = 'Payment failed'

        if latest_tx:
            data = {
                'state': 'cancel',
                'reference': latest_tx.reference,
                'moyasar_payment_id': payment_id,
            }
            try:
                latest_tx.sudo()._process('moyasar', data)
            except Exception as exc:
                _logger.error('Error processing failed transaction %s: %s', latest_tx.id, exc)
                try:
                    latest_tx.write({'moyasar_payment_id': payment_id, 'state': 'cancel'})
                    latest_tx._set_canceled()
                except Exception:
                    pass
        else:
            _logger.warning(
                'Payment failed for invoice %s but no transaction to cancel', invoice.id
            )

        return request.render('muk_payment_moyasar.payment_error_temp', {
            'error': error_message,
            'redirect': '/payment/status',
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Transaction lookup helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _latest_tx_on_invoice(self, invoice):
        txs = invoice.transaction_ids.sorted('create_date', reverse=True)
        return txs[0] if txs else None

    def _latest_tx_on_order(self, order):
        txs = order.transaction_ids.sorted('create_date', reverse=True)
        return txs[0] if txs else None

    # ─────────────────────────────────────────────────────────────────────────
    # Frontend config endpoint
    # ─────────────────────────────────────────────────────────────────────────

    @http.route(['/get/moyasar/order'], type='jsonrpc', auth='public', website=True)
    def get_moyasar_order_config(self, **post):
        """
        Return Moyasar public key, amount, currency, and description to the
        frontend JS widget.

        Resolves order/invoice from:
          - portal_order.orderId              portal sale order
          - portal_order.portal_order         sale order by ID
          - portal_order.pos_order            POS order
          - portal_order.portal_invoice_order invoice portal
          - portal_order.generate_link_sale_order  generated link
          - portal_order.generate_link_invoice     generated link
          - portal_order.saas_invoice_id      SaaS direct invoice
          - session sale_order_id             website cart fallback
        """
        portal_order = post.get('portal_order', {})
        pos_order = False
        order = None

        if portal_order.get('orderId'):
            order = request.env['sale.order'].sudo().browse(
                int(portal_order['orderId'])
            )
        elif portal_order.get('portal_order'):
            order = request.env['sale.order'].sudo().search(
                [('id', '=', int(portal_order['portal_order']))], limit=1
            )
        elif portal_order.get('pos_order'):
            order = request.env['pos.order'].sudo().search(
                [('id', '=', int(portal_order['pos_order']))]
            )
            pos_order = True
        elif portal_order.get('portal_invoice_order'):
            order = request.env['account.move'].sudo().browse(
                int(portal_order['portal_invoice_order'])
            )
        elif portal_order.get('generate_link_sale_order'):
            order = request.env['sale.order'].sudo().browse(
                int(portal_order['generate_link_sale_order'])
            )
        elif portal_order.get('generate_link_invoice'):
            order = request.env['account.move'].sudo().browse(
                int(portal_order['generate_link_invoice'])
            )
        elif portal_order.get('saas_invoice_id'):
            order = request.env['account.move'].sudo().browse(
                int(portal_order['saas_invoice_id'])
            )
            _logger.info('get_moyasar_order_config: SaaS direct invoice %s', order.id)
        else:
            sale_order_id = request.session.get('sale_order_id')
            order = sale_order_id and request.env['sale.order'].sudo().browse(sale_order_id)
            _logger.info('get_moyasar_order_config: session sale_order_id=%s', sale_order_id)

        if not order or not order.exists():
            _logger.error(
                'get_moyasar_order_config: could not resolve order/invoice from post=%s', post
            )
            return {'success': False, 'error': 'Order or invoice not found'}

        if pos_order:
            amount = order.amount_total
        elif hasattr(order, 'tax_totals') and order.tax_totals:
            amount = order.tax_totals.get('total_included', order.amount_total)
        else:
            amount = order.amount_total

        description = str(order.name) if order and order.exists() else ''
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'moyasar')], limit=1
        )

        return {
            'success': True,
            'amount': amount,
            'public_key': provider.moyasar_public_key if provider else '',
            'callback_url': base_url,
            'currency': order.currency_id.name if order.currency_id else '',
            'description': description,
        }
