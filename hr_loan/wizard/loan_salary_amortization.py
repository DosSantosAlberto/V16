import datetime

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, Warning


class LoanSalaryAmortization(models.TransientModel):
    _name = 'hr.loan.salary.amortization'
    _description = 'Loan or Salary Amortization'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    loan_id = fields.Many2one('hr.loan', string='Loan or Salary Advance')
    loan_line_ids = fields.One2many('loan.salary.amortization.line', 'amortization_id', string="Loan Line")
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    company_id = fields.Many2one('res.company', 'Company', readonly=False, help="Company",
                                 default=lambda self: self.env.user.company_id, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, help="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id, tracking=True)
    installments = fields.Integer('Nº Of Installments', default=1)
    parcel_for_amortize = fields.Integer('Parcels to Amortize', compute='_compute_parcel_for_amortize')
    total_amount = fields.Monetary('Total Amount', compute='_compute_total_amount')
    total_amount_facade = fields.Monetary('Total Amount')
    received_amount = fields.Monetary('Received Amount')

    @api.depends('loan_line_ids')
    def _compute_total_amount(self):
        total_amount = 0.0
        for res in self:
            for line in res.loan_line_ids:
                total_amount += line.amount
        self.total_amount = total_amount

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.loan_id = False
        self.loan_line_ids = [(5, 0, 0)]

    @api.onchange('loan_line_ids')
    def onchange_method(self):
        total_amount = 0.0
        for res in self:
            for line in res.loan_line_ids:
                total_amount += line.amount
        self.total_amount_facade = total_amount

    @api.depends('loan_line_ids')
    def _compute_parcel_for_amortize(self):
        self.parcel_for_amortize = self.env['hr.loan.line'].search_count(
            [('loan_id', '=', self.loan_id.id), ('paid', '=', False)])

    @api.onchange('installments', 'loan_id')
    def onchange_installments_loan(self):
        self.loan_line_ids = False
        loan_lines = self.env['hr.loan.line'].search([('loan_id', '=', self.loan_id.id), ('paid', '=', False)],
                                                     limit=self.installments)

        for line in loan_lines:
            self.loan_line_ids = [(0, 0, {
                'amount': line.amount,
                'date': line.date,
                'paid': line.paid,
                'line_id': line.id,
                'loan_id': line.loan_id.id,
            })]

    def action_amortize(self):
        if self.received_amount >= self.total_amount_facade:
            for line in self.loan_line_ids:
                if line:
                    loan_line = self.env['hr.loan.line'].search(
                        [('id', '=', line.line_id.id), ('loan_id', '=', self.loan_id.id)])
                    if loan_line:
                        loan_line.write({'paid': True})
                        loan_line.loan_id._compute_loan_amount()
            values = {
                'date': fields.datetime.today(),
                'amount': self.total_amount_facade,
                'origin': 'Amortization',
                'loan_id': self.loan_id.id,
                'installment': self.installments,
                'received_amount': self.received_amount
            }
            self.loan_id.payment_historic_line = [(0, 0, values)]
            self.loan_id.attachment_ids |= self.attachment_ids
            self.update_remuneration_deduction(self.loan_id)
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Amortization made successfully... thank you!',
                    'type': 'rainbow_man',
                }
            }
        else:
            raise Warning(_('Insufficient amount to amortize the installments.'))

    def update_remuneration_deduction(self, loan_id):
        loan_line = self.env['hr.loan.line'].search([('loan_id', '=', loan_id.id), ('paid', '=', False)])
        if loan_id.request_type == 'loan':
            remuneration_code_id = self.env.ref('hr_loan.hr_remuneration_code_descontoemprestimo').id
        elif loan_id.request_type == 'salary_advance':
            remuneration_code_id = self.env.ref('hr_loan.hr_remuneration_code_desconto_adia_salario').id
        if loan_line:
            date = loan_line[0].date
            remuneration_line = self.env['hr.remuneration'].search(
                [('contract_id', '=', loan_id.employee_contract_id.id), ('remunerationcode_id', '=', remuneration_code_id)])
            if remuneration_line:
                remuneration_line.write({
                    'date_start': date
                })
        if not loan_line:
            remuneration_line = self.env['hr.remuneration'].search(
                [('contract_id', '=', loan_id.employee_contract_id.id), ('remunerationcode_id', '=', remuneration_code_id)])
            if remuneration_line.is_loan:
                remuneration_line.unlink()


class LoanSalaryAmortizationLine(models.TransientModel):
    _name = 'loan.salary.amortization.line'

    amount = fields.Float(string="Amount", required=False, help="Amount")
    paid = fields.Boolean(string="Paid", help="Paid")
    amortization_id = fields.Many2one('hr.loan.salary.amortization')
    date = fields.Date(string="Payment Date", help="Date of the payment")
    line_id = fields.Many2one('hr.loan.line', string="Line Id")
    loan_id = fields.Many2one('hr.loan', string='Loan or Salary Advance')
