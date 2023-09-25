from odoo import api, models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_entity = fields.Char("Entity")
    agt_cert_number = fields.Char("Software Validation Number", readonly=True, default="207/AGT/2019")
    agt_product_name = fields.Char("Product ID", readonly=True, default="ODOO - CBSHS")
    agt_product_version = fields.Char("Product Version", readonly=True, default="")
    audit_file_version = fields.Char("Audit File Version", readonly=True, default="1.01_01")
    key_version = fields.Char(string="Key Version", default="1")
    product_company_name = fields.Char("Product Company Name", readonly=True,
                                       default="CENTRAL BUSINESS SOLUTIONS, LDA")
    product_company_website = fields.Char("Website", readonly=True, default="www.compllexus.com")
    product_company_tax_id = fields.Char("Product Company Tax ID", readonly=True, default="5420002159")
    agt_regime = fields.Selection([('e', 'Exclusão de IVA'), ('s', 'Simplificado'), ('g', 'Geral')], 'Regime')
    c_invoice_sequence_int = fields.Integer('ISI')
