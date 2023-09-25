from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def create(self, values):
        if any({"code"} & set(values.keys())) and self.env.company.country_id.code == "AO":
            if values["code"] == 'OU' or values["code"] == 'OR' or values["code"] == 'PP':
                if values.get("company_id") == False:
                    values["company_id"] = self.env.company.id
        return super(IrSequence, self).create(values)

    # def write(self, values):
    #     if any({"suffix", "prefix", "company_id"} & set(values.keys())):
    #         if values.get("company_id"):
    #             if self.company_id:
    #                 return {}
    #         elif values.get("company_id") == False:
    #             return {}
    #         return super(IrSequence, self).write(values)
    #     return {}

    def unlink(self):
        for sequence in self:
            if sequence.code == 'OU' or sequence.code == 'OR' or sequence.code == 'PP':
                raise UserError(_(
                    "the sequence %s was not deleted, as it has an associated document type. Contact the administrator") % sequence.name)
            super(IrSequence, sequence).unlink()
        return {}
