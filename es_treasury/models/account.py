import json
from datetime import datetime, timedelta

from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        number_to_reconcile = number_to_check = last_balance = 0
        has_at_least_one_statement = False
        bank_account_balance = nb_lines_bank_account_balance = 0
        outstanding_pay_account_balance = nb_lines_outstanding_pay_account_balance = 0
        title = ''
        number_draft = number_waiting = number_late = to_check_balance = 0
        sum_draft = sum_waiting = sum_late = 0.0
        if self.type in ('bank', 'cash'):
            last_statement = self._get_last_bank_statement(
                domain=[('move_id.state', '=', 'posted')])
            last_balance = last_statement.balance_end
            has_at_least_one_statement = bool(last_statement)
            bank_account_balance, nb_lines_bank_account_balance = self._get_journal_bank_account_balance(
                domain=[('move_id.state', '=', 'posted')])
            outstanding_pay_account_balance, nb_lines_outstanding_pay_account_balance = self._get_journal_outstanding_payments_account_balance(
                domain=[('move_id.state', '=', 'posted')])

            self._cr.execute('''
                SELECT COUNT(st_line.id)
                FROM account_bank_statement_line st_line
                JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
                JOIN account_bank_statement st ON st_line.statement_id = st.id
                WHERE st_line_move.journal_id IN %s
                AND st.state = 'posted'
                AND NOT st_line.is_reconciled
            ''', [tuple(self.ids)])
            number_to_reconcile = self.env.cr.fetchone()[0]

            to_check_ids = self.to_check_ids()
            number_to_check = len(to_check_ids)
            to_check_balance = sum([r.amount for r in to_check_ids])
        # TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')
            self.env['account.move'].flush(
                ['amount_residual', 'currency_id', 'move_type', 'invoice_date', 'company_id', 'journal_id', 'date',
                 'state', 'payment_state'])

            (query, query_args) = self._get_open_bills_to_pay_query()
            self.env.cr.execute(query, query_args)
            query_results_to_pay = self.env.cr.dictfetchall()

            (query, query_args) = self._get_draft_bills_query()
            self.env.cr.execute(query, query_args)
            query_results_drafts = self.env.cr.dictfetchall()

            (query, query_args) = self._get_late_bills_query()
            self.env.cr.execute(query, query_args)
            late_query_results = self.env.cr.dictfetchall()

            curr_cache = {}
            (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(query_results_to_pay, currency,
                                                                                curr_cache=curr_cache)
            (number_draft, sum_draft) = self._count_results_and_sum_amounts(query_results_drafts, currency,
                                                                            curr_cache=curr_cache)
            (number_late, sum_late) = self._count_results_and_sum_amounts(late_query_results, currency,
                                                                          curr_cache=curr_cache)
            read = self.env['account.move'].read_group([('journal_id', '=', self.id), ('to_check', '=', True)],
                                                       ['amount_total'], 'journal_id', lazy=False)
            if read:
                number_to_check = read[0]['__count']
                to_check_balance = read[0]['amount_total']
        elif self.type == 'general':
            read = self.env['account.move'].read_group([('journal_id', '=', self.id), ('to_check', '=', True)],
                                                       ['amount_total'], 'journal_id', lazy=False)
            if read:
                number_to_check = read[0]['__count']
                to_check_balance = read[0]['amount_total']

        is_sample_data = self.kanban_dashboard_graph and any(
            data.get('is_sample_data', False) for data in json.loads(self.kanban_dashboard_graph))

        return {
            'number_to_check': number_to_check,
            'to_check_balance': formatLang(self.env, to_check_balance, currency_obj=currency),
            'number_to_reconcile': number_to_reconcile,
            'account_balance': formatLang(self.env, currency.round(bank_account_balance), currency_obj=currency),
            'amount_balance':  currency.round(bank_account_balance),
            'has_at_least_one_statement': has_at_least_one_statement,
            'nb_lines_bank_account_balance': nb_lines_bank_account_balance,
            'outstanding_pay_account_balance': formatLang(self.env, currency.round(outstanding_pay_account_balance),
                                                          currency_obj=currency),
            'nb_lines_outstanding_pay_account_balance': nb_lines_outstanding_pay_account_balance,
            'last_balance': formatLang(self.env, currency.round(last_balance) + 0.0, currency_obj=currency),
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_late': number_late,
            'sum_draft': formatLang(self.env, currency.round(sum_draft) + 0.0, currency_obj=currency),
            'sum_waiting': formatLang(self.env, currency.round(sum_waiting) + 0.0, currency_obj=currency),
            'sum_late': formatLang(self.env, currency.round(sum_late) + 0.0, currency_obj=currency),
            'currency_id': currency.id,
            'bank_statements_source': self.bank_statements_source,
            'title': title,
            'is_sample_data': is_sample_data,
            'company_count': len(self.env.companies)
        }
