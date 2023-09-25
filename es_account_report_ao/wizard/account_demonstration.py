from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class AccountDemoNat(models.TransientModel):
    _name = 'account.demonstration'
    _description = 'Report Model for balance'
    _rec_name = 'company_id'

    accounting_year = fields.Many2one(comodel_name='account.fiscal.year', string="Ano Fiscal",
                                      default=lambda self: self.env.user.company_id.accounting_year)
    company_id = fields.Many2one(comodel_name="res.company", default=lambda self: self.env.user.company_id,
                                 string="Empresa")

    date_from = fields.Date(string='Data de Início', related='accounting_year.date_from')

    date_to = fields.Date(string='Date de Fim', related='accounting_year.date_to')

    enable_filter = fields.Boolean(string='Fazer Comparação', default=False)

    type = fields.Selection(
        [('nature', 'NATURE'), ('function', 'FUNCTION')], string='Type')

    target_move = fields.Selection(
        [('all', 'Todas as entradas lançadas'), (
            'post', 'Todas as entradas'), ],
        default="all", string="Movimentos Contabilísticos Específicos")

    def print(self):
        if self.type == 'function':
            return self.env.ref('es_account_report_ao.action_account_demonstration_fun_report').report_action(self)
        return self.env.ref('es_account_report_ao.action_account_demonstration_nat_report').report_action(self)

    # @api.onchange('enable_filter')
    # def _onchange_filter(self):
    #     if self.enable_filter:
    #         prev_accounting_year = self.env['account.fiscal.year'].search([
    #             ('company_id', '=', self.company_id.id),
    #             ('name', '=', str(int(self.accounting_year.name)-1))
    #         ])
    #
    #         if prev_accounting_year:
    #             return prev_accounting_year[0]
    #         else:
    #             self.enable_filter = False
    #             raise ValidationError(_('Não existe registro de ano anterior'))

    def prev_accounting_year(self):
        prev_accounting_year = self.env['account.fiscal.year'].search([
            ('company_id', '=', self.company_id.id),
            ('name', '=', str(int(self.accounting_year.name) - 1))
        ])
        if prev_accounting_year:
            return prev_accounting_year[0]

    def format(self, value):
        return formatLang(self.env, value, currency_obj=self.company_id.currency_id)

    def get_account_balance(self, codes, date_from, date_to):
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]

        if isinstance(codes, list):
            for code in codes:
                domain.append(('account_id.code', '=like', f'{code}%'))
        else:
            domain.append(('account_id.code', '=like', f'{codes}%'))

        if self.target_move == 'posted':
            domain.append(('move_id.state', '=', 'posted'))

        return sum(self.env['account.move.line'].search(domain).mapped('balance'))
