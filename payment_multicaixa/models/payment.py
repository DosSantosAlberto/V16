from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
import datetime
from dateutil.parser import parse
import requests
import json
import logging
import hashlib, binascii
import hmac
import sys
import pprint

_logger = logging.getLogger(__name__)

_multicaixa_status_mapping = {'active': 'authorized', 'paid': 'done', 'expired': 'cancel', 'deleted': ''}

class PaymentProviderMulticaixa(models.Model):
    _inherit = 'payment.provider'

    _payments_events_url = "/payments"
    _ack_payment_url = "/payments/%s"
    _generate_ref_url = "/references"
    _generate_ref_url = "/reference_ids"
    _get_ref_url = "/references/%s"

    head = {"Accept": "application/vnd.proxypay.v2+json",
            "Content-type": "application/json"}

    code = fields.Selection(selection_add=[('multicaixa', 'Multicaixa')], ondelete={'multicaixa': 'set default'})
    entity_reference = fields.Char('Entity Reference', size=5, default="00000", required=False)
    multicaixa_api_key = fields.Char("API Key", size=64, required_if_provider="multicaixa", groups="base.group_system")
    reference_validation = fields.Boolean("Validate Reference")
    max_expiry_days = fields.Integer("Max days to expire")

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist PayUmoney providers when the currency is not INR. """
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name != 'AOA':
            providers = providers.filtered(lambda p: p.code != 'multicaixa')

        return providers

    def _get_multicaixa_urls(self, environment):
        environment = 'prod' if self.state == 'enabled' else 'test'
        if environment == 'prod':
            return {
                'multicaixa_form_url': '/payment/multicaixa/reference',
                'multicaixa_rest_url': 'https://api.proxypay.co.ao',
            }
        else:
            return {
                'multicaixa_form_url': '/payment/multicaixa/reference',
                'multicaixa_rest_url': 'https://api.sandbox.proxypay.co.ao',
            }

    def multicaixa_form_generate_values(self, tx_values):
        self.ensure_one()
        expiry_date = datetime.date.today() + datetime.timedelta(days=self.max_expiry_days)
        multicaixa_tx_values = dict(tx_values)

        multicaixa_tx_values.update({
            'order': tx_values['reference'],
            'expiry_date': expiry_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'entity_reference': self.entity_reference,
            'client_name': tx_values.get('partner_first_name') + ' ' + tx_values.get('partner_last_name'),
            'email': tx_values.get('partner_email'),
            'phone': tx_values.get('partner_phone'),
            'amount': '{0:.2f}'.format(tx_values.get('amount')),
            'error': True and tx_values.get('amount') > 99999999.99 or False
        })
        return multicaixa_tx_values

    def multicaixa_get_form_action_url(self):
        self.ensure_one()
        return self._get_multicaixa_urls(self.state)['multicaixa_form_url']

    def generate_new_reference(self, tx_values):
        endpoint_url = self._get_multicaixa_urls(self.state)['multicaixa_rest_url'] + self._generate_ref_url
        _logger.info('Multicaixa: Send post message to: %s', endpoint_url)
        response = requests.post(endpoint_url, headers=self.head, auth=('api', self.multicaixa_api_key))
        return {'amount': tx_values['amount'], 'end_datetime': tx_values['expiry_date'], 'response': response}

    def create_update_reference(self, tx_values):
        endpoint_url = self._get_multicaixa_urls(self.state)['multicaixa_rest_url'] + self._get_ref_url
        _logger.info('Multicaixa: Send post message to: %s', endpoint_url)

        parameters = {
            'amount': tx_values['amount'],
            'end_datetime': tx_values['expiry_date'],
            'custom_fields': {'id': tx_values['order'], 'name': tx_values['client_name'],
                              'email': tx_values['email'], 'tlm': tx_values['phone']}}
        payload = json.dumps(parameters)
        response = requests.put(endpoint_url % tx_values['reference_id'], data=payload, headers=self.head,
                                auth=('api', self.multicaixa_api_key))
        return response

    @api.model
    def cron_get_payments(self):
        multicaixa_provider = self.env["payment.provider"].search([('code', '=', 'multicaixa')], limit=1)
        multicaixa_provider[0].get_payment_events()

    def get_payment_events(self):
        ack_payment_ids = []
        endpoint_url = self._get_multicaixa_urls(self.state)['multicaixa_rest_url'] + self._payments_events_url
        response = requests.get(endpoint_url, headers=self.head, auth=('api', self.multicaixa_api_key))
        _logger.info('Multicaixa: get payments events: %s', pprint.pformat(response.text))
        if response.status_code == 200:
            payments = json.loads(response.text)
            for payment in payments:
                tx = self.env['payment.transaction'].search([('reference_id', '=', payment['reference_id']), ], limit=1)
                if tx:
                    _logger.info('Multicaixa: Found transaction with id: %s', payment['reference_id'])
                    payment['order'] = payment['custom_fields']['id']
                    tx.sudo()._process_notification_data(payment)
                    self.acknowledge_payments(payment['id'])
                    _logger.info('Multicaixa: Delete payment transaction with id: %s and reference %s',
                                 payment['id'], payment['reference_id'])
                else:
                    _logger.info('Multicaixa: Not Found transaction with id: %s', payment['reference_id'])
        return

    def get_references(self):
        endpoint_url = self._get_multicaixa_urls(self.state)['multicaixa_rest_url'] + self._generate_ref_url
        response = requests.get(endpoint_url, headers=self.head, auth=('api', self.api_key))
        _logger.info('Multicaixa: get references : %s', pprint.pformat(response.text))
        if response.status_code == 200:
            references = json.loads(response.text).get('references')
            for reference in references:
                tx = self.env['payment.transaction'].search([('payment_reference', '=', reference['number']), ],
                                                            limit=1)
                if tx:
                    _logger.info('Multicaixa: Found reference with id: %s', reference['number'])
                    tx.write({
                        'state': _multicaixa_status_mapping[reference['status']],
                    })
                    # TODO: Add notification to the client warning that is order was cancelled due to payment
                    if tx.state == 'cancel':
                        tx.sale_order_id.with_context(send_email=True).write({'state': 'cancel'})
        return

    def validate_signature(self, payment, signature, body_data):
        validation_signature = hmac.new(str(self.api_key), body_data, hashlib.sha256)
        calc_signature = validation_signature.hexdigest().upper()
        _logger.info('Multicaixa: validate signature form proxypay %s vs validation signature %s',
                     signature, calc_signature)
        if hmac.compare_digest(signature.encode('ascii'), validation_signature.hexdigest().upper()):
            return True
        return False

    def delete_reference(self, id):
        endpoint_url = self._get_multicaixa_urls(self.state)['multicaixa_rest_url'] + self._get_ref_url
        requests.delete(endpoint_url % id, auth=('api', self.api_key))
        return True

    def acknowledge_payments(self, id):
        endpoint_url = self._get_multicaixa_urls(self.state)['multicaixa_rest_url'] + self._ack_payment_url
        response = requests.delete(endpoint_url % id, auth=('api', self.multicaixa_api_key))
        return response


class MulticaixaTransaction(models.Model):
    _inherit = 'payment.transaction'

    _mock_payment_url = "/payments"

    reference_id = fields.Char('Reference ID', size=15)
    entity_reference = fields.Char('Entity Ref')
    expiry_date = fields.Date("Expire Date")
    tx_id = fields.Char('Transaction Id')
    test_payment_sent = fields.Boolean("Test Payment Sent")
    terminal_transaction_id = fields.Char('Terminal Transaction Id')
    terminal_location = fields.Char('Terminal Location')
    terminal_id = fields.Char("Terminal Id")
    terminal_type = fields.Char("Terminal Type")
    payment_date = fields.Datetime("Payment Date")

    def _get_post_processing_values(self):
        """ Return a dict of values used to display the status of the transaction.

        For a provider to handle transaction status display, it must override this method and
        return a dict of values. Provider-specific values take precedence over those of the dict of
        generic post-processing values.

        The returned dict contains the following entries:

        - `provider_code`: The code of the provider.
        - `reference`: The reference of the transaction.
        - `amount`: The rounded amount of the transaction.
        - `currency_id`: The currency of the transaction, as a `res.currency` id.
        - `state`: The transaction state: `draft`, `pending`, `authorized`, `done`, `cancel`, or
          `error`.
        - `state_message`: The information message about the state.
        - `is_post_processed`: Whether the transaction has already been post-processed.
        - `landing_route`: The route the user is redirected to after the transaction.
        - Additional provider-specific entries.

        Note: `self.ensure_one()`

        :return: The dict of processing values.
        :rtype: dict
        """
        self.ensure_one()
        res = super()._get_post_processing_values()
        if self.provider_code != 'multicaixa':
            return res

        res['entity_reference'] = self.provider_id.entity_reference
        res['reference_id'] = self.reference_id
        res['expiry_date'] = self.expiry_date
        res['display_message'] = self.provider_id.pending_msg
        return res

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Flutterwave-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'multicaixa':
            return res
        expiry_date = datetime.date.today() + datetime.timedelta(days=self.provider_id.max_expiry_days)
        rendering_values = dict(processing_values)
        partner_id = self.env["res.partner"].sudo().browse(processing_values['partner_id'])
        rendering_values.update({
            'order': processing_values['reference'],
            'expiry_date': expiry_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'entity_reference': self.provider_id.entity_reference,
            'client_name': partner_id.name,
            'email': partner_id.email,
            'phone': partner_id.mobile or partner_id.phone,
            'amount': '{0:.2f}'.format(processing_values.get('amount')),
            'error': True and processing_values.get('amount') > 99999999.99 or False
        })

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values.update({
            'api_url': self.provider_id.multicaixa_get_form_action_url(),
        })
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Find the transaction based on the notification data.

        For a provider to handle transaction processing, it must overwrite this method and return
        the transaction matching the notification data.

        :param str provider_code: The code of the provider handling the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction, if found.
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'multicaixa' or len(tx) == 1:
            return tx

        reference = notification_data.get('order')
        if not reference:
            error_msg = 'Multicaixa: no reference data received'

            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = 'Multicaixa: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx

    def _process_notification_data(self, notification_data):
        """ Update the transaction state and the provider reference based on the notification data.

        This method should usually not be called directly. The correct method to call upon receiving
        notification data is :meth:`_handle_notification_data`.

        For a provider to handle transaction processing, it must overwrite this method and process
        the notification data.

        Note: `self.ensure_one()`

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'multicaixa':
            return

        if notification_data.get('status_code') == 200:
            self.write({
                'reference_id': notification_data.get('reference_id'),
                'tx_id': notification_data.get('id'),
                'expiry_date': fields.Date.to_date(parse(notification_data.get('expiry_date'))),
                'entity_reference': notification_data.get('entity_id'),
                'provider_reference': notification_data.get('entity_id'),
                "fees": notification_data.get('fee'),
            })
            self._set_pending()
            return True
        elif notification_data.get('terminal_id'):
            self.sudo().write({
                "terminal_type": notification_data['terminal_type'],
                "provider_reference": notification_data['terminal_transaction_id'],
                "terminal_transaction_id": notification_data['terminal_transaction_id'],
                #"payment_id": notification_data['terminal_transaction_id'],
                "terminal_location": notification_data['terminal_location'],
                "terminal_id": notification_data['terminal_id'],
                "payment_date": parse(notification_data['datetime']).replace(tzinfo=None),
                'tx_id': notification_data['id'],
                'expiry_date': fields.Date.to_date(parse(notification_data['period_end_datetime']).date()),
                'entity_reference': notification_data['entity_id'],
                "fees": notification_data['fee'],
            })
            self._set_done()
            return True
        else:
            self.write({
                'state': 'error',
                'tx_id': notification_data.get('id'),
                'state_message': notification_data.get('message'),
            })

    @api.model
    def _multicaixa_form_get_tx_from_data(self, data):
        reference = data.get('order')
        if not reference:
            error_msg = 'Multicaixa: no reference data received'

            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = 'Multicaixa: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx

    def push_payment_events(self, payment):
        self.write({
            'state': 'done',
            'reference_id': payment['reference_id'],
            'payment_date': parse(payment['datetime']).replace(tzinfo=None),
            'terminal_location': payment['terminal_location'],
            'terminal_transaction_id': payment['terminal_transaction_id'],
            'terminal_type': payment['terminal_type'],
            "terminal_id": payment['terminal_id'],
            "fees": payment['fee'],
        })
        self.set_transaction_done()
        self.acquirer_id.acknowledge_payments(payment['id'])
        return True

    @api.model
    def cron_create_payment_test(self):
        transactions = self.env["payment.transaction"].search([('state', '=', 'pending')], limit=1)
        for transaction in transactions.filtered(lambda t: t.provider_id.state == 'test'):
            transaction.test_payment_events()

    def test_payment_events(self):
        endpoint_url = self.provider_id._get_multicaixa_urls(self.provider_id.state)[
                           'multicaixa_rest_url'] + self._mock_payment_url
        parameters = {
            'reference_id': self.reference_id,
            'amount': self.amount,
        }

        payload = json.dumps(parameters)
        json_response = requests.post(endpoint_url, data=payload, headers=self.provider_id.head,
                                      auth=('api', self.provider_id.multicaixa_api_key))
        if json_response.status_code == 200:
            self.test_payment_sent = True
            return
        else:
            raise ValidationError(json_response.text)


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['multicaixa'] = {'mode': 'one', 'domain': [('type', '=', 'bank')]}
        return res
