# -*- coding: utf-8 -*-
import time
import babel
from odoo import models, fields, api, tools, _
from datetime import datetime


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    loan_line_id = fields.Many2one('hr.loan.line', string="Loan Installment", help="Loan installment")


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    loan_line_id = fields.Many2one('hr.loan.line', string="Loan Installment", help="Loan installment")


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # @api.onchange('employee_id', 'date_from', 'date_to')
    # def onchange_employee(self):
    #     if (not self.employee_id) or (not self.date_from) or (not self.date_to):
    #         return
    #
    #     employee = self.employee_id
    #     date_from = self.date_from
    #     date_to = self.date_to
    #     contract_ids = []
    #
    #     ttyme = datetime.fromtimestamp(time.mktime(time.strptime(str(date_from), "%Y-%m-%d")))
    #     locale = self.env.context.get('lang') or 'en_US'
    #     self.name = _('Salary Slip of %s for %s') % (
    #         employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
    #     self.company_id = employee.company_id
    #
    #     if not self.env.context.get('contract') or not self.contract_id:
    #         # contract_ids = self.get_contract(employee, date_from, date_to)
    #
    #         contract_ids = employee._get_contracts(date_from, date_to)
    #         if not contract_ids:
    #             return
    #         self.contract_id = self.env['hr.contract'].browse(contract_ids[0])
    #
    #     if not self.contract_id.salary_structure:
    #         return
    #     self.struct_id = self.contract_id.structure_type_id.default_struct_id
    #
    #     # computation of the salary input
    #     contracts = self.env['hr.contract'].browse(contract_ids)
    #     worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
    #     worked_days_lines = self.worked_days_line_ids.browse([])
    #     for r in worked_days_line_ids:
    #         worked_days_lines += worked_days_lines.new(r)
    #     self.worked_days_line_ids = worked_days_lines
    #     if contracts:
    #         input_line_ids = self.get_inputs(contracts, date_from, date_to)
    #         input_lines = self.input_line_ids.browse([])
    #         for r in input_line_ids:
    #             input_lines += input_lines.new(r)
    #         self.input_line_ids = input_lines
    #     return

    # def get_inputs(self, contract_ids, date_from, date_to):
    #     """This Compute the other inputs to employee payslip.
    #                        """
    #     res = super(HrPayslip, self).get_inputs(contract_ids, date_from, date_to)
    #     contract_obj = self.env['hr.contract']
    #     emp_id = contract_obj.browse(contract_ids[0].id).employee_id
    #     lon_obj = self.env['hr.loan'].search([('employee_id', '=', emp_id.id), ('state', '=', 'approve')])
    #     for loan in lon_obj:
    #         for loan_line in loan.loan_lines:
    #             if date_from <= loan_line.date <= date_to and not loan_line.paid:
    #                 for result in res:
    #                     if result.get('code') == 'LO':
    #                         result['amount'] = loan_line.amount
    #                         result['loan_line_id'] = loan_line.id
    #     return res

    def process_loan(self, contract_id, date_from, date_to):

        res = self.line_ids

        contract_obj = self.env['hr.contract']
        # employee_id = contract_obj.browse(contract_ids[0].id).employee_id
        employee_id = contract_id.employee_id
        lon_obj = self.env['hr.loan'].search([('employee_id', '=', employee_id.id), ('state', '=', 'approve')])
        for loan in lon_obj:
            for loan_line in loan.loan_lines:
                if date_from <= loan_line.date <= date_to and not loan_line.paid:
                    for result in res:
                        if result.code == 'LO':
                            result.loan_line_id = loan_line.id
                        if result.code == 'SAR':
                            result.loan_line_id = loan_line.id
        return res

    def compute_sheet(self):
        for res in self:
            res.process_loan(res.contract_id, res.date_from, res.date_to)
        super(HrPayslip, self).compute_sheet()

    def action_payslip_done(self):
        for res in self:
            res.process_loan(res.contract_id, res.date_from, res.date_to)
            for line in res.line_ids:
                if line.loan_line_id:
                    if res.date_from <= line.loan_line_id.date <= res.date_to and not line.loan_line_id.paid:
                        line.loan_line_id.paid = True
                        line.loan_line_id.loan_id._compute_loan_amount()
                        values = {
                            'date': fields.datetime.today(),
                            'amount': line.loan_line_id.amount,
                            'origin': 'Payslip',
                            'loan_id': line.loan_line_id.id,
                            'received_amount': line.loan_line_id.amount
                        }
                        line.loan_line_id.loan_id.payment_historic_line = [(0, 0, values)]
                        res.update_remuneration_deduction(line.loan_line_id.loan_id)
        return super(HrPayslip, self).action_payslip_done()

    def update_remuneration_deduction(self, loan_id):
        loan_line = self.env['hr.loan.line'].search([('loan_id', '=', loan_id.id), ('paid', '=', False)])
        if loan_id.request_type == 'loan':
            remuneration_code_id = self.env.ref('hr_loan.hr_remuneration_code_descontoemprestimo').id
        elif loan_id.request_type == 'salary_advance':
            remuneration_code_id = self.env.ref('hr_loan.hr_remuneration_code_desconto_adia_salario').id
        if loan_line:
            date = loan_line[0].date
            remuneration_line = self.env['hr.remuneration'].search(
                [('contract_id', '=', loan_id.employee_contract_id.id),
                 ('remunerationcode_id', '=', remuneration_code_id)])
            if remuneration_line:
                remuneration_line.write({
                    'date_start': date
                })
        if not loan_line:
            remuneration_line = self.env['hr.remuneration'].search(
                [('contract_id', '=', loan_id.employee_contract_id.id),
                 ('remunerationcode_id', '=', remuneration_code_id)])
            if remuneration_line.is_loan:
                remuneration_line.unlink()
