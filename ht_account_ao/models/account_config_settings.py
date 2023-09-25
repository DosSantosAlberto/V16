from odoo import fields, models, api, _


class AOAccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_fiscal_year = fields.Many2one(related='company_id.accounting_year', required=1, readonly=False)
    invoice_cost_center = fields.Boolean(related='company_id.invoice_cost_center', readonly=False)
