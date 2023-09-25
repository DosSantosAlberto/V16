import pprint
import logging
import werkzeug
from odoo.exceptions import ValidationError
from odoo import http, _
from odoo.http import request
import json


_logger = logging.getLogger(__name__)


# https://developer.proxypay.co.ao/
class MulticaixaController(http.Controller):
    _process_url = '/payment/custom/process'
    return_url = '/shop/payment/validate'

    @http.route('/payment/multicaixa/reference', type='http', auth='public', methods=['POST'], website=True)
    def multicaixa_form_feedback(self, **post):
        payment_data = {}
        _logger.info('Multicaixa: entering api key authentication  and request new reference: %s', pprint.pformat(post))
        multicaixa = request.env['payment.provider'].search([('code', '=', 'multicaixa')], limit=1)

        proxypay_response = multicaixa.generate_new_reference(post)
        json_response = proxypay_response['response']
        if json_response.status_code >= 400:
            _logger.info('Error %s:.',
                         json_response.status_code)
        if json_response and post:
            payment_data['reference_id'] = json.loads(json_response.text)
            payment_data['order'] = post['order']
            payment_data['expiry_date'] = proxypay_response['end_datetime']
            # data = json.loads(json_response.text).get('reference')
            payment_data['status_code'] = json_response.status_code
            payment_data['amount'] = post['amount']

            post['expiry_date'] = proxypay_response['end_datetime']
            post['reference_id'] = payment_data['reference_id']
            multicaixa.create_update_reference(post)
            request.env['payment.transaction'].sudo()._handle_notification_data('multicaixa', payment_data)
        return request.redirect('/payment/status')


    @http.route('/payment/multicaixa/push', type='json', auth='none', csrf=False, methods=['POST'])
    def multicaixa_push_payment(self, **post):
        _logger.info('Multicaixa: entering push payment event  %s', pprint.pformat(request.jsonrequest))
        multicaixa = request.env['payment.provider'].sudo().search([('provider', '=', 'multicaixa')], limit=1)
        payment = json.loads(request.jsonrequest.text)
        signature = request.headers.get("X-Signature")
        body = request.jsonrequest.text
        if multicaixa.validate_signature(payment, signature, body):
            tx = request.env['payment.transaction'].sudo().search([('reference_id', '=', payment['reference_id'])],
                                                                  limit=1)
            if tx.push_payment_events(payment):
                return 200
        return -1
