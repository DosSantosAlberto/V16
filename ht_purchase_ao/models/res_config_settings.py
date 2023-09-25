from odoo import fields, models, api, _


class AOAccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    purchase_cost_center = fields.Boolean(related='company_id.purchase_cost_center', readonly=False)
