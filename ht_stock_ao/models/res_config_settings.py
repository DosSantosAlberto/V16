from odoo import fields, models, api, _


class AOAccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    stock_cost_center = fields.Boolean(related='company_id.stock_cost_center', readonly=False)
