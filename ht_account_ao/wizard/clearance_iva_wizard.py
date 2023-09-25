from datetime import datetime
from odoo import fields, models, api
from odoo.exceptions import ValidationError
import time
from dateutil.relativedelta import relativedelta


class ClearanceIvaWizard(models.TransientModel):
    _name = 'clearance.iva.wizard'

    year = fields.Many2one(comodel_name='account.fiscal.year',
                           default=lambda self: self.env.user.company_id.accounting_year, string='Ano Fiscal')
    date_start = fields.Date(default=time.strftime('%Y-%m-1'))
    date_end = fields.Date(
        default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    @api.constrains('date_start', 'date_end')
    def check_date(self):
        if self.date_end < self.date_start:
            raise ValidationError(('Data Final não pode ser Menor que a data inicial'))

    def make_iva_clearance(self):
        year = self.year
        company_id = self.env.user.company_id.id

        period = self.env['account.fiscal.period'].search(
            [('company_id', '=', company_id), ('year.name', '=', year.name), ('period', '=', '14')])
        period = period[0] if period else self.env['account.fiscal.period'].create({
            'period': '14',
            'start_date': year.date_from,
            'end_date': year.date_to,
            'year': year.id,
            'company_id': company_id
        })

        journal = self.env['account.journal'].search([('name', 'ilike', 'apuramento'), ('company_id', '=', company_id)])
        journal = journal[0] if journal else self.env['account.journal'].create({
            'name': 'Apuramento',
            'type': 'general',
            'company_id': company_id,
            'code': 'APU',
        })

        move = self.env['account.move'].create({
            'ref': f"Apuramento de iva do ano fiscal {datetime.strftime(year.date_to, '%Y')}",
            'period': period.id,
            'journal_id': journal.id,
            'year': year.id,
            'date': self.date_end,
            'company_id': company_id,
        })

        move.make_iva_clerance(self.date_end, self.date_start)

        # if not move.line_ids: raise ValidationError(
        #     'impossível apurar o IVA porque não foram encontrados lançamentos nas contas de IVA'.capitalize())

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": move.id
        }
