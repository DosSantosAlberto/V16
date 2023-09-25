from odoo import models, fields, api


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    tax_exigibility = fields.Selection(selection_add=[('withholding', 'Withholding')])
    threshold_wht = fields.Float("Threshold Amount", default=0,
                                 help="Withholding Tax will be applied only if base amount >= to threshold amount")
    code = fields.Char(string="Code")
    exemption_reason = fields.Char(string="Exemption Reason")
    tax_type = fields.Char(string="Tax Type")
    tax_code = fields.Char(string="Tax Code")


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tax_exigibility = fields.Selection(selection_add=[('withholding', 'Withholding')])
    threshold_wht = fields.Float("Threshold Amount", default=0,
                                 help="Withholding Tax will be applied only if base amount >= to threshold amount")
    code = fields.Char(string="Code", compute="_compute_code")
    exemption_reason = fields.Char(string="Exemption Reason")
    tax_type = fields.Char(string="Tax Type")
    tax_code = fields.Char(string="Tax Code")

    @api.depends("name", "amount", "type_tax_use")
    def _compute_code(self):
        for tax in self:
            if tax.name:
                new_code = (
                    tax.name.split(" ")[0] if tax.name.split(" ")[0] != "Retenção" else "RF"
                )
            else:
                new_code = "RF"

            active = '1' if tax.active else '0'

            new_code = (new_code + str(tax.amount) + tax.type_tax_use + active).upper()
            tax.code = new_code
