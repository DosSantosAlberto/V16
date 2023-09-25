from odoo import fields, models, api, _
from odoo.exceptions import Warning, UserError, ValidationError


class SalaryCategory(models.Model):
    _inherit = 'hr.salary.rule.category'

    def write(self, values):
        result = []
        for record in self:
            if values.get("code"):
                if record.code in ["BASIC", "ALW", "GROSS", "DED", "NET", "COMP", "ABOINSS", "ABOIRT", "ABOINSSIRT",
                                   "DEDINSSIRT", "INSS", "IRT"]:
                    raise UserError(
                        _("This category rule is Protected it's possible to change code.\n Contact System Administrator."))
            result = super(SalaryCategory, self).write(values)
        return result

    def unlink(self):
        for record in self:
            if record.code in ["BASIC", "ALW", "GROSS", "DED", "NET", "COMP", "ABOINSS", "ABOIRT", "ABOINSSIRT",
                               "DEDINSSIRT", "INSS", "IRT"]:
                raise UserError(_(
                    "The category %s was not deleted, as it has an associated Salary Rules. Contact the administrator") % record.name)
            super(SalaryCategory, record).unlink()
        return {}


class SalaryRecordRules(models.Model):
    _inherit = 'hr.salary.rule'

    def write(self, values):
        result = []
        for record in self:
            # if values.get("code"):
            #     if record.code in ['BASE', 'CHEF', 'NAT', 'PREM', 'REPR', 'ATA', 'sub_not', 'FER',
            #                        'CORES', 'sub_ren_casa', 'RENDES', 'FALH', 'FAMI', 'TRAN', 'ALIM', 'FALTA']:
            #         raise UserError(
            #             _('This record rule as Protected dont is Possible to update code.\n Contact System Administrator.'))
            result = super(SalaryRecordRules, self).write(values)
        return result

    def unlink(self):
        for record in self:
            if record.code in ['BASE', 'CHEF', 'NAT', 'PREM', 'REPR', 'ATA', 'sub_not', 'FER',
                               'CORES', 'sub_ren_casa', 'RENDES', 'FALH', 'FAMI', 'TRAN', 'ALIM', 'FALTA']:
                raise UserError(_(
                    "The record rule %s was not deleted, as it has an associated Salary Rules. Contact the administrator") % record.name)

            super(SalaryRecordRules, self).unlink()
        return {}
