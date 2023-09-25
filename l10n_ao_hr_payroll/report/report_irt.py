# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from dateutil.parser import parse
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from . import report_common


class ReportIRT(models.AbstractModel):
    _name = 'report.l10n_ao_hr_payroll.report_irt'
    _description = 'IRT Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = None
        period_date_obj = None
        if 'form' not in data:
            raise ValidationError('This action is under development')

        slip_filter_by = data['form']['slip_filter_by']
        if slip_filter_by == 'payslip_batch':
            slip_id = data['form']['hr_payslip_run_id'][0]
            docs = self.env['hr.payslip'].search(
                [('payslip_run_id', '=', slip_id), ('company_id', '=', self.env.company.id)], order="employee_id")
            period_date = self.env['hr.payslip.run'].browse(slip_id).date_end
        else:
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            if type(end_date) is str:
                period_date = parse(end_date)
            else:
                period_date = end_date
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date),
                                                  ('company_id', '=', self.env.company.id)], order="employee_id")

        if not docs:
            raise ValidationError('There is no payslips that match this criteria')

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'time': time,
            'xpto': 'this is the value of xpto',
            'formatLang': formatLang,
            'env': self.env,
            'period': '%s/%d' % (report_common.get_month_text(period_date.month), period_date.year)
        }
