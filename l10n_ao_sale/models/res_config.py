from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    document_type_id = fields.Many2one("sale.order.document.type", "Document Type")


class ResConfig(models.TransientModel):
    _inherit = "res.config.settings"

    document_type_id = fields.Many2one(related="company_id.document_type_id", readonly=False)
    country_id = fields.Many2one(related="company_id.country_id",readonly=True)