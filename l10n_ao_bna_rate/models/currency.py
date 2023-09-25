from odoo import api, fields, models, _
import logging
import requests
import re
from datetime import date

_logger = logging.getLogger(__name__)

class Currency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def update_rates(self):

        for cur in self.env["res.currency"].search([("active", "=", True), ("id", "!=", self.env.company.currency_id.id)]):
            try:
                url = f"https://www.bna.ao/service/rest/taxas/get/taxa/referencia?moeda={cur.name.lower()}&tipocambio=b"
                response = (requests.get(url, verify=False)).text
                response = response.replace("true", "True")
                response = response.replace("false", "False")
                data = eval(response)
                if data['success']:
                    rate = float(data['genericResponse'][0]['taxa'])

                if not len(self.env['res.currency.rate'].search([('name', '=', date.today()),
                                                                 ('company_id', '=', 1), ('currency_id', '=', cur.id)])):
                    self.env['res.currency.rate'].create({'currency_id': cur.id, 'company_id': 1, 'rate': 1.0 / rate})
            except Exception as err:
                _logger.error(_("An error occourred while trying to get the rates for currency %s, with following "
                                "error \n %s") % (cur.name, err))

# class CurrencyRate(models.Model):
#     _inherit = 'res.currency.rate'
#
#     bank_id = fields.Many2one("res.bank")

