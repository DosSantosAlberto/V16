import time
from datetime import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# import time
# from datetime import date
# from datetime import datetime
# from datetime import timedelta
# from dateutil import relativedelta
# from openerp.tools.translate import _
# from openerp.exceptions import UserError
# import calendar

# from openerp import api, fields, models


class WizardSalary(models.TransientModel):
    _name = 'wizard.bank'
    _description = 'Print BANK Map'

    bank = fields.Many2one('res.bank', string='Bank', required='True', help='Select the bank for print the declaration')
    slip_filter_by = fields.Selection([('payslip_batch', 'Bayslip Batch'), ('payslip_date', 'Payslip Date')],
                                      'Filter By', required=True,
                                      help='Select the methond to capture the Payslips. You can choose Payslip Batch or by Date')
    hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
                                        help='Select the Payslip Batch for wich you want do generate the Salary map Report')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be lower than End Date')

    def print_report(self):
        return self.env.ref('l10n_ao_hr_payroll.action_report_bank').report_action(self, data={
            'form': self.read(['bank', 'slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date'])[0]})
