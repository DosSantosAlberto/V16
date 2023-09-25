from odoo import fields, models, api


class HrPayment(models.Model):
    _name = 'hr.payment'
    _description = 'Employee Payment'

    name = fields.Char(string="Ref")

    date = fields.Date(string="Date", default=fields.Date.today)
    company_id = fields.Many2one(comodel_name="res.company", string="Company", related='payslip_run_id.company_id')
    journal_id = fields.Many2one(comodel_name="account.journal", string="Journal")
    payslip_run_id = fields.Many2one(comodel_name="hr.payslip.run", string="PaySlip Batch")
    lines = fields.One2many('hr.payment.line', 'hr_payment', 'Payment Line')
    state = fields.Selection([
        ('treasury', 'In Treasury'), ('paid', 'Paid'),
    ], string="State", default="treasury")
    amount_paid = fields.Float(string="Amount Paid")


class HrPaymentLine(models.Model):
    _name = 'hr.payment.line'
    _description = 'Employee Payment Line'

    hr_payment = fields.Many2one(comodel_name="hr.payment")
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee")
    irt_amount = fields.Float(string="IRT Amount")
    ss_amount = fields.Float(string="SS Amount")
    amount = fields.Float(string="Processed Amount")
    amount_paid = fields.Float(string="Amount Paid")
    amount_debt = fields.Float(string="Amount Debt")
