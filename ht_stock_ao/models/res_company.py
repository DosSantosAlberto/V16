from odoo import api, models, fields, api, _


class HtResCompany(models.Model):
    _inherit = 'res.company'

    stock_cost_center = fields.Boolean(string="Stock Cost Center")
