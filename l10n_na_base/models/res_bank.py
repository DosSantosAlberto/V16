from odoo import models, fields
from odoo.addons.base_iban.models import res_partner_bank

class ResBank(models.Model):
    _inherit = "res.bank"

    code = fields.Char("Code", size=6)

    _sql_constraints = [
        ('name_code_uniq', 'unique(code)', 'The code of the bank must be unique!')
    ]

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    show_doc = fields.Boolean("Show on documents")

res_partner_bank._map_iban_template['ao'] = 'AOkk nnnn nnnn nnnn nnnn nnnn n' #Angola
