from odoo import fields, models, api, _


class AOAccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_cost_center = fields.Boolean(related='company_id.sale_cost_center', readonly=False)
