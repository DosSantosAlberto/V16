from odoo import fields, models, api, _


class PayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'
    _description = 'Salary Structure'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # @api.model
    # def create(self, values):
    #     result = super(PayrollStructure, self).create(values)
    #     rule_ids = result.rule_ids.filtered(lambda r: r.code in ["BASIC", "GROSS", "NET"])
    #     if rule_ids:
    #         rule_ids.unlink()
    #     return result


class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'

    sequence_view = fields.Integer(string='Sequence View', related='sequence')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def write(self, vals):
        if not vals.get('struct_id'):
            vals['struct_id'] = self.env.ref('l10n_ao_hr_payroll.hr_salary_structure_base').id
        return super(SalaryRule, self).write(vals)
