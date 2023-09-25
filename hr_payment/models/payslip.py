from odoo import fields, models, api


class HrPayslipBatch(models.Model):
    _inherit = 'hr.payslip.run'

    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ], string="Payment State", default='not_paid')

    def post_treasury(self):
        for res in self:
            if res.payment_state in ['not_paid']:
                vals = {
                    'name': res.name,
                    'payslip_run_id': res.id,
                    'state': 'treasury',
                }
                slip_lines = [(5, 0, 0)]
                for slip in res.slip_ids:
                    slip_lines.append((0, 0, {
                        'employee_id': slip.employee_id.id,
                        'amount': slip.total_paid,
                        'irt_amount': slip.amount_irt * -1 if slip.amount_irt < 0 else 0.0,
                        'ss_amount': ((slip.total_remunerations * 0.08) + (slip.amount_inss * -1)) if res.structure_type_id.type == 'employee' else 0.0
                    }))
                vals['lines'] = slip_lines
                hr_payment = self.env['hr.payment'].create(vals)
                res._prepare_account_payment(hr_payment)
                res.payment_state = 'in_payment'

    def _prepare_account_payment(self, hr_payment):
        """

        :param hr_payment:
        :return:
        """
        for res in self:
            vals = {
                'name': hr_payment.name,
                'journal_id': res.journal_id.id,
                'payment_type': 'outbound',
                'partner_type': 'employee',
                'hr_payment': hr_payment.id,
                'payment_method': 'transfer',
                'amount': sum([line.amount for line in hr_payment.lines])
            }
            hr_payment_lines = [(5, 0, 0)]
            for line in hr_payment.lines:
                hr_payment_lines.append((0, 0, {
                    'name': line.employee_id.name,
                    'employee_type': line.employee_id.employee_type,
                    'amount': line.amount,
                    'irt_amount': line.irt_amount,
                    'ss_amount': line.ss_amount,
                }))
            vals['lines'] = hr_payment_lines
            self.env['account.payment.salary'].create(vals)
