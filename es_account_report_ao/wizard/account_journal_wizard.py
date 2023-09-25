from datetime import datetime
from odoo import fields, models, api
from odoo.tools.misc import formatLang
import time
from dateutil.relativedelta import relativedelta


class AccountJournalWizard(models.TransientModel):
    _name = 'account.journal.wizard'
    _description = 'Account Extract Wizard'

    journal_id = fields.Many2one('account.journal', string="journal")
    date_from = fields.Date('Date From', default=time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.company, string="Company")
    account_group_id = fields.Many2one(comodel_name='account.group', string='Group')
    filter_by = fields.Selection([('journal', 'Journal')],
                                 string='Filter By', default='Journal',required=True)

    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')

    def get_account_movements(self):
        if self.filter_by == 'journal':
            moves_list = []
            account_moves = []
            total_period_credit = total_period_debit = 0.0
            if self.target_move == 'posted':
                account_moves = self.env['account.move.line'].search(
                    [('journal_id', '=', self.journal_id.id), ('date', '>=', self.date_from),
                     ('date', '<=', self.date_to),
                     ('company_id', '=', self.company_id.id), ('move_id_state', '=', 'posted')], order='date asc')

            if self.target_move == 'all':
                account_moves = self.env['account.move.line'].search(
                    [('journal_id', '=', self.journal_id.id), ('date', '>=', self.date_from),
                     ('date', '<=', self.date_to),
                     ('company_id', '=', self.company_id.id), ('move_id_state', '=', 'posted')], order='date asc')



            for record in account_moves:

                total_period_credit += float(record['credit'])
                total_period_debit += float(record['debit'])
                total_accumulated_credit = total_period_credit
                total_accumulated_debit = total_period_debit

                data = {
                    'id': record.id,
                    'account': record.account_id.id,
                    'date': record.date,
                    'journal': record.journal_id,
                    'move': record.move_id,
                    'reason': record.reason_code,
                    'integrator': record.integrator_code,
                    'partner': record.partner_id,
                    'reference': record.ref,
                    'journal_number': record.matching_number,
                    'description': record.name,
                    'tax': record.tax_ids.id,
                    'analytic': record.analytic_account_id.id,
                    'debit': record.debit,
                    'credit': record.credit,
                    'total_period_credit': formatLang(self.env, abs(total_period_credit)),
                    'total_period_debit': formatLang(self.env, abs(total_period_debit)),
                    'total_accumulated_debit': formatLang(self.env, abs(total_accumulated_debit)),
                    'total_accumulated_credit': formatLang(self.env, abs(total_accumulated_credit)),
                }
                moves_list.append(data)
            return moves_list


    def print_report(self):
        return self.env.ref('es_account_report_ao.action_account_journal_report').report_action(self)
