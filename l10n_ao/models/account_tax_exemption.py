from odoo import models,fields, api


class TaxExemptionReason(models.Model):

    _name = "account.tax.exemption"
    _description = "Tax exemption reason"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")


    def name_get(self):
        res = []
        for record in self:
            name = record.name
            code = record.code
            name = '[%s] %s' % (code, name)
            res.append((record.id, name))
        return res
