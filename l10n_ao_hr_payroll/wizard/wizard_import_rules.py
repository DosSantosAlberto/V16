import time
from datetime import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WizardImportRules(models.TransientModel):
    _name = 'wizard.import.rules'
    _description = 'Import Rules From Other Company'

    company_id = fields.Many2one('res.company', string='Company')



    def import_rules(self):
        rules_salary = self.env["hr.salary.rule"]
        rules = self.env['hr.salary.rule'].search([('company_id', "=", self.company_id.id)])
        for ru in rules:
            rules_import = {
                "name": ru.name,
                "category_id": ru.category_id.id,
                "code": ru.code,
                "sequence": ru.sequence,
                "struct_id": ru.struct_id.id,
                "active": True,
                "appears_on_payslip": ru.appears_on_payslip,
                "company_id": self.env.company.id,
                "condition_select": ru.condition_select,
                "note": ru.note,
                "amount_select": ru.amount_select,
                "amount_percentage_base": ru.amount_percentage_base,
                "quantity": ru.quantity,
                "amount_percentage": ru.amount_percentage,
            }
            rules_salary.create(rules_import)
