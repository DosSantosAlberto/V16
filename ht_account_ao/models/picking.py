from odoo import models, api, fields, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_cost_center = fields.Boolean(related='company_id.stock_cost_center')
    cost_center = fields.Many2one('account.cost.center', string="Cost Center")
