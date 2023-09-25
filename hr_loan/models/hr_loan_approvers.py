from odoo import fields, models, api


class HrLoanApproves(models.Model):
    _name = 'hr.loan.approves'
    _description = 'Loan or Salary Advance Approvers'

    user_id = fields.Many2one('res.users', string="User")
    employee_id = fields.Many2one('hr.employee', related='user_id.employee_id')
