from datetime import datetime
from odoo import fields, models, api
from odoo.tools.misc import formatLang
import time
from dateutil.relativedelta import relativedelta


class Amortization(models.Model):
    _inherit = 'account.asset'

    open_date = fields.Date('Open Date', default=time.strftime('2022-01-31'))
    date_out = fields.Date('Out Date', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    is_import = fields.Boolean('Is import?', help='Se o produto foi importado ou não')
    number = fields.Integer('Utility Number')
    acquisition = fields.Boolean('Acquisition')
    tax = fields.Float('Tax', default=25)
    tax_corrected = fields.Float('Tax Corrected', default=25)


class Amortization(models.TransientModel):
    _name = 'amortization.map.wizard'
    _description = "Amortization Map"

    date_from = fields.Date('Date From', default=time.strftime('2018-01-01'))
    date_to = fields.Date('Date To', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id, string="Company")
    accounting_year = fields.Many2one(comodel_name='account.fiscal.year', string="Ano Fiscal",
                                      default=lambda self: self.env.user.company_id.accounting_year)

    nature_assets = fields.Selection(
        [('tangible', 'Activos Fixos Tangíveis'), ('Intangibles', 'Activos Fixos Intangívei'),
         ('biological', 'Activos Biológicos Não'), ('investment', 'Propriedade de Investimento'), ('other', 'Outros')])
    other_nature_assets = fields.Char('Outra Naturesa')
    other_constants = fields.Selection([('constant', 'Quotas Constantes'), ('other', 'Outro')])
    other_description_constants = fields.Char('Outro')

    def amortization_before(self, product=None):
        r = int(str(self.date_to)[0:4]) - 1
        r = str(r) + "-01-01"
        for rec in product:
            for k in rec.depreciation_move_ids:
                if str(k.date)[0:4] == r[0:4]:
                    return k.asset_remaining_value
        return 0.0

    def get_account_mother(self):
        mother_account = self.env['account.account'].search(
            [('code', 'in', ['113', '1139', '114', '115', '1152', '119'])],
            order='code,name')
        return mother_account

    def get_amortization_all(self, code):
        cod = code[0].code if code[0].code == '1152' or code[0].code == '1139' else code[0].code + "1"
        list_data = []
        list_inf = self.env['account.asset'].search(
            [('acquisition_date', '>=', self.date_from), ('acquisition_date', '<=', self.date_to),
             ('state', '=', 'open'), ('account_asset_id.code', '=', cod)],
            order='account_asset_id, name')
        for rec in list_inf:
            data = {
                'code': rec.account_asset_id.code,
                'name': rec.name,
                'acq_month': str(rec.acquisition_date)[::-1][3:5][::-1] if rec.acquisition_date else " ",
                'acq_year': str(rec.acquisition_date)[0:4] if rec.acquisition_date else " ",
                'opera_m': str(rec.first_depreciation_date)[::-1][3:5][::-1] if rec.first_depreciation_date else " ",
                'opera_y': str(rec.first_depreciation_date)[0:4] if rec.first_depreciation_date else " ",
                'is_import': 'Sim' if str(rec.is_import) else "Não",
                'acquisition_value': rec.original_value,
                'duration': rec.method_number,
                'valor_total_revaluation': rec.original_value,
                'valor_before': self.amortization_before(rec),
                'tax': rec.tax,
                'tax_corrected': rec.tax_corrected,
                'values': rec.original_value * rec.tax / 100,
                'value_depreciation': (rec.original_value * rec.tax / 100),
                'value_accounting': rec.original_value + rec.original_value * rec.tax,

            }
            list_data.append(data)
        return {'data': list_data, 'total_original': sum(rec['acquisition_value'] for rec in list_data),
                'valor_total_revaluation': sum(rec['valor_total_revaluation'] for rec in list_data),
                'valor_before': sum(rec['valor_before'] for rec in list_data),
                'values': sum(rec['values'] for rec in list_data),
                'value_depreciation': sum(rec['value_depreciation'] for rec in list_data),
                'value_accounting': sum(rec['value_accounting'] for rec in list_data)}

    def amortization_account_move_line(self):
        rec = self.env['account.move.line'].search(
            [('date', '>=', self.date_from), ('date', '<=', self.date_to), ('account_id.code', 'in', ['124', '129'])],
            order='account_id')
        return rec

    def print(self):
        return self.env.ref('es_account_report_ao.action_amortization_map_report').report_action(self)
