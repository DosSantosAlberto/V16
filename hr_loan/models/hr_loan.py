# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError, ValidationError


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"

    @api.model
    def default_get(self, field_list):
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            ts_user_id = result['user_id']
        else:
            ts_user_id = self.env.context.get('user_id', self.env.user.id)
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
        return result

    def _compute_loan_amount(self):
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid

    name = fields.Char(string="Loan Name", default="/", readonly=True, help="Name of the loan", tracking=True)
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date", tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, help="Employee", tracking=True)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department", help="Employee", tracking=True)
    installment = fields.Integer(string="No Of Installments", default=1, help="Number of installments", tracking=True)
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today(),
                               help="Date of the paymemt", tracking=True)
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    payment_historic_line = fields.One2many('hr.loan.payment.historic', 'loan_id', string="Payment Historic Line",
                                            index=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id,
                                 states={'draft': [('readonly', False)]}, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, help="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id, tracking=True)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position",
                                   help="Job position", tracking=True)
    loan_amount = fields.Float(string="Loan Amount", required=True, help="Loan amount", tracking=True)
    total_amount = fields.Float(string="Total Amount", store=True, readonly=True, compute='_compute_loan_amount',
                                help="Total loan amount", tracking=True)
    balance_amount = fields.Float(string="Balance Amount", store=True, compute='_compute_loan_amount',
                                  help="Balance amount", tracking=True)
    total_paid_amount = fields.Float(string="Total Paid Amount", store=True, compute='_compute_loan_amount',
                                     help="Total paid amount", tracking=True)
    end_date = fields.Date('End Date')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, tracking=True, default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_loan.group_hr_loan_own_documents').id)])

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', tracking=True)

    loan_purpose = fields.Char('Loan Purpose', tracking=True)
    request_type = fields.Selection([('loan', 'Loan'), ('salary_advance', 'Salary Advance')], string='Request Type',
                                    tracking=True)
    salary_advance_reson = fields.Char('Advance Reason', tracking=True)
    employee_contract_id = fields.Many2one('hr.contract', string='Contract', related='employee_id.contract_id')
    term_and_condition = fields.Boolean('Terms and Conditions')
    loan_approvers_line_ids = fields.One2many('hr.loan.approves.line', 'hr_loan_id', string='Approvers')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.model
    def create(self, values):
        loan_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', values['employee_id']), ('state', '=', 'approve'),
             ('balance_amount', '!=', 0), ('request_type', '=', values['request_type'])])
        if loan_count:
            raise ValidationError(_("The employee has already a pending installment"))
        else:
            if values.get('loan_purpose'):
                values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
            elif values.get('salary_advance_reson'):
                values['name'] = self.env['ir.sequence'].get('hr.loan.salary.advance.seq') or ' '
            res = super(HrLoan, self).create(values)
            return res

    @api.constrains('date')
    def check_loan_or_advance(self):
        today = datetime.today()
        start_date = datetime(today.year, 1, 1)
        end_date = datetime(today.year, 12, 31)

        loan_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', self.employee_id.id), ('request_type', '=', self.request_type),
             ('date', '>=', start_date), ('date', '<=', end_date)])
        if self.request_type == 'loan':
            if loan_count > self.company_id.loan_per_year:
                raise ValidationError(_("The employee reached the limit per year!"))
        if self.request_type == 'salary_advance':
            if loan_count > self.company_id.salary_advance_per_year:
                raise ValidationError(_("The employee reached the limit per year!"))

    @api.onchange('request_type', 'employee_id')
    def _onchange_request_type(self):
        approvers = self.env['hr.loan.approves'].search([])
        self.loan_approvers_line_ids = False
        for approver in approvers:
            self.loan_approvers_line_ids = [(0, 0, {
                'user_id': approver.user_id.id
            })]

    def compute_installment(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            end_date = loan.payment_date + relativedelta(months=loan.installment - 1)
            if loan.check_contract(end_date):
                loan.loan_lines.unlink()
                date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
                amount = loan.loan_amount / loan.installment
                loan.end_date = end_date
                for i in range(1, loan.installment + 1):
                    self.env['hr.loan.line'].create({
                        'date': date_start,
                        'amount': amount,
                        'employee_id': loan.employee_id.id,
                        'loan_id': loan.id})
                    date_start = date_start + relativedelta(months=1)
                loan._compute_loan_amount()
            else:
                raise ValidationError(
                    _('Employee cannot make a loan. Please check the contract expiry date or contact HR Manager.'))
        return True

    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_submit(self):
        if self.loan_lines:
            self.write({'state': 'waiting_approval_1'})
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Request Submitted Success: Thank you!',
                    'type': 'rainbow_man',
                }
            }
        if not self.loan_lines:
            raise ValidationError(_("Please Compute installment"))

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_approve(self):
        if self.request_type == 'loan':
            remuneration_code_id = self.env.ref('hr_loan.hr_remuneration_code_descontoemprestimo').id
        elif self.request_type == 'salary_advance':
            remuneration_code_id = self.env.ref('hr_loan.hr_remuneration_code_desconto_adia_salario').id
        remuneration_id = self.env['hr.remuneration.code'].search([('id', '=', remuneration_code_id)])
        loan_amount = self.loan_lines[0].amount
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                contract = self.employee_contract_id
                values = {
                    'remuneration_ids': [(0, 0, {
                        'remunerationcode_id': remuneration_code_id,
                        'rem_type': 'deduction',
                        'date_start': data.payment_date,
                        'date_end': data.end_date,
                        'amount': loan_amount,
                        'name': remuneration_id.name,
                        'is_loan': True
                    })]
                }
                contract.write(values)
                if contract:
                    self.write({'state': 'approve'})

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(
                    'You cannot delete a loan/salary advance which is not in draft or cancelled state')
        return super(HrLoan, self).unlink()

    def check_contract(self, date_to):
        contract = self.env['hr.contract'].search(
            [('id', '=', self.employee_contract_id.id), ('state', '=', 'open'), ('date_end', '>=', date_to)])
        if contract:
            return True
        return False

    @api.onchange('installment')
    def onchange_installment(self):
        if self.installment > self.company_id.company_installment_loan_limit:
            raise ValidationError(_('You can not pay in %d prestations. Please contact your HR Manager!') % self.installment)

    @api.constrains('installment')
    def constrains_installment(self):
        if self.installment > self.company_id.company_installment_loan_limit:
            raise ValidationError(_('You can not pay in %d prestations. Please contact your HR Manager!') % self.installment)

    @api.constrains('term_and_condition')
    def constrains_term_and_condition(self):
        if not self.term_and_condition:
            raise ValidationError(
                _('You cannot make this operation without accept the terms and conditions. Please contact your HR Manager!'))
        if not len(self.loan_approvers_line_ids) >= 1:
            raise ValidationError(
                _('You cannot make this operation without any approver line. Please contact your HR Manager!'))


class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=False, help="Date of the payment")
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee")
    amount = fields.Float(string="Amount", required=False, help="Amount")
    paid = fields.Boolean(string="Paid", help="Paid")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", help="Loan")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.", help="Payslip")


class InstallmentPaymentHistoric(models.Model):
    _name = "hr.loan.payment.historic"
    _description = "Installment Payment Historic"

    date = fields.Date(string="Payment Date", help="Date of the payment")
    amount = fields.Float(string="Amount", help="Amount")
    installment = fields.Integer('Installment', default=1)
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", help="Loan")
    origin = fields.Char('Origin')
    received_amount = fields.Float('Received Amount')


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_employee_loans(self):
        """This compute the loan amount and total loans count of an employee.
            """
        self.loan_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', self.id), ('request_type', '=', 'loan')])
        self.salary_advance_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', self.id), ('request_type', '=', 'salary_advance')])

    loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')
    salary_advance_count = fields.Integer(string="Salary Advance Count", compute='_compute_employee_loans')


class HrLoanApproveLine(models.Model):
    _name = 'hr.loan.approves.line'
    _description = 'Loan Approves Line'

    user_id = fields.Many2one('res.users', string="User")
    employee_id = fields.Many2one('hr.employee', related='user_id.employee_id')
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    sign_date = fields.Date('Sign Date')
    state = fields.Selection([('new', 'New'), ('pending', 'Pending'), ('approved', 'Approved'), ('refused', 'Refused')],
                             string='State', default='new')
    hr_loan_id = fields.Many2one('hr.loan', string='Loan or Salary Advance')

    def btn_approve(self):
        if self.env.user.id == self.user_id.id:
            self.sign_date = fields.datetime.today()
            self.state = 'approved'
            self.salray_loan_approve_state()
        else:
            raise ValidationError(_('Only this user %s can sign this request!') % self.user_id.employee_id.name)

    def btn_refused(self):
        if self.env.user.id == self.user_id.id:
            self.sign_date = fields.datetime.today()
            self.state = 'refused'
            self.salray_loan_approve_state()
        else:
            raise ValidationError(_('Only this user %s can sign this request!') % self.user_id.employee_id.name)

    def salray_loan_approve_state(self):
        approvals = self.env['hr.loan.approves.line'].search([('hr_loan_id', '=', self.hr_loan_id.id)])
        approves_count = len(approvals)
        count = 0
        for approve in approvals:
            if self.hr_loan_id.state == 'waiting_approval_1':
                if approve.state == 'approved':
                    count = count + 1
                if approve.state == 'refused':
                    self.hr_loan_id.action_refuse()
        if count == approves_count:
            self.hr_loan_id.action_approve()
