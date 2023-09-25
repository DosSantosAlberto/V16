from odoo import fields, models, api, _


class AOAccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_company_name = fields.Char(related="company_id.product_company_name",)
    product_company_website = fields.Char(related="company_id.product_company_website",)
    product_company_tax_id = fields.Char(related="company_id.product_company_tax_id",)
    software_validation_number = fields.Char(related="company_id.agt_cert_number")
    product_id = fields.Char(related="company_id.agt_product_name")
    product_version = fields.Char(related="company_id.agt_product_version")
    audit_file_version = fields.Char(related="company_id.audit_file_version")
    key_version = fields.Char(related="company_id.key_version")
    agt_regime = fields.Selection(related="company_id.agt_regime")
    c_invoice_sequence_int = fields.Integer(related="company_id.c_invoice_sequence_int")
