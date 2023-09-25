# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from dateutil.parser import parse
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class ReportINSS(models.AbstractModel):
    _name = 'report.l10n_ao_hr_payroll.report_inss'
    _description = 'INSS Report'

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
                [('payslip_run_id', '=', slip_id), ('employee_id.is_foreign', '=', False),
                 ('company_id', '=', self.env.company.id)], order="employee_id")
            period_date = self.env['hr.payslip.run'].browse(slip_id).date_end
        else:
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            if type(end_date) is str:
                period_date = parse(end_date)
            else:
                period_date = end_date
            docs = self.env['hr.payslip'].search(
                [('date_to', '>=', start_date), ('date_to', '<=', end_date), ('employee_id.is_foreign', '=', False),
                 ('company_id', '=', self.env.company.id)], order="employee_id")

        if not docs:
            raise ValidationError('There is no payslips that match this criteria')

        months = {
            1: _('January'),
            2: _('February'),
            3: _('March'),
            4: _('April'),
            5: _('May'),
            6: _('June'),
            7: _('July'),
            8: _('August'),
            9: _('September'),
            10: _('October'),
            11: _('November'),
            12: _('December'),
        }

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'time': time,
            'xpto': 'this is the value of xpto',
            'formatLang': formatLang,
            'env': self.env,
            'period': '%s/%d' % (months[period_date.month], period_date.year)
        }

        # return self.env['report'].render('ag_hr.report_inss', docargs)
