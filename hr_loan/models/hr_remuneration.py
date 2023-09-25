from odoo import fields, models, api, _
from odoo.exceptions import AccessDenied


class HrRemuneration(models.Model):
    _inherit = 'hr.remuneration'
    is_loan = fields.Boolean('Is Loan or Salary Advance')

    def unlink(self):
        """Rever este codigo"""
        for line in self:
            if line.contract_id:
                loan_id = self.env['hr.loan'].search(
                    [('employee_contract_id', '=', line.contract_id.id), ('state', 'in', ['waiting_approval_1', 'approve'])])

                if loan_id:
                    if loan_id[-1]:
                        for loan_line in loan_id[-1].loan_lines:
                            if not loan_line.paid and line.is_loan:
                                raise AccessDenied(
                                    _('You can not remove this line. Employee has Loan ou Salary Advance. Please contact the '
                                      'system administrator!'))
        return super(HrRemuneration, self).unlink()
