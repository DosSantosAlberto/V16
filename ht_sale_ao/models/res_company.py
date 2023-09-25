from odoo import api, models, fields, api, _


class HtResCompany(models.Model):
    _inherit = 'res.company'

    sale_cost_center = fields.Boolean(string="Sale Cost Center")
