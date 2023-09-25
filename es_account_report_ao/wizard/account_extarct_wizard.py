from datetime import datetime
from odoo import fields, models, api
from odoo.tools.misc import formatLang
import time
from dateutil.relativedelta import relativedelta



class AccountExtractWizard(models.TransientModel):
    _name = 'account.extract.wizard'
    _description = 'Account Extract Wizard'

    account_id = fields.Many2one('account.account', string="Account")
    date_from = fields.Date('Date From', default=time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.company, string="Company")
    account_group_id = fields.Many2one(comodel_name='account.group', string='Group')
    filter_by = fields.Selection([('account', 'Account'), ('cost_center', 'Cost Center'),
                                  ('cash_flow', 'Cash Flow'), ('fiscal_plan', 'Fiscal Plan'), ('iva_plan', 'IVA Plan')],
                                 string='Filter By', default='account')
    display_account = fields.Selection([('all', 'All'), ('movement', 'Movement')], string='Display Account',
                                       default='movement')
    specific_account = fields.Boolean('Specifc Account?')
    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    cash_flow = fields.Many2one(comodel_name="account.cash.flow", string="Cash Flow")
    iva_plan = fields.Many2one(comodel_name="account.iva", string="Plan IVA")
    fiscal_plan = fields.Many2one(comodel_name="account.fiscal.plan", string="Plan Fiscal")
    by_account = fields.Boolean(string="By Account?")
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')

    @api.onchange('filter_by')
    def onchange_filter_by(self):
        self.by_account = False
        self.specific_account = False
        self.account_id = False

    def account_setup(self, account_code):
        account = self.env['account.account'].search([('code', '=', account_code)])
        return {'account_id': account.id, 'account_code': account.code, 'account_name': account.name}

    def _args_query(self):
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'move_id_states': tuple([self.target_move] if self.target_move == 'posted' else ['posted', 'draft'])
        }

    def query_account_movements(self, account):
        _query = """
                   SELECT account.name As account_name, line.date, journal.name As journal_name, journal.id As journal, SUM(line.debit) AS debit, SUM(line.credit) AS credit, SUM(line.balance) AS balance, move.ref as description, move.name As doc
                   FROM account_move_line line
                    INNER JOIN account_account account ON
                        line.account_id = account.id
                    INNER JOIN account_journal journal ON
                        line.journal_id = journal.id 
                    INNER JOIN account_move move ON
                        line.move_id = move.id
                   WHERE (line.account_id = %(account_id)s)
                       AND (line.date >= %(date_from)s)
                       AND (line.date <= %(date_to)s)
                       AND (line.company_id = %(company_id)s)
                       AND (line.move_id_state IN %(move_id_states)s)
                   GROUP BY account.name, line.date, journal.name, journal.id, move.name, move.ref
               """

        data = []
        balance = 0.0
        balance_debit = 0.0
        balance_credit = 0.0
        current_balance = 0.0
        args = self._args_query()
        args['account_id'] = account
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            balance = row['balance']
            row['balance_debit'] = 0.0  # start
            row['balance_credit'] = 0.0  # start

            if row['credit'] > row['debit']:
                current_balance -= balance
                balance_credit += row['credit']
                row['current_balance'] = current_balance
                row['balance_credit'] = balance_credit
                row['balance_type'] = 'C'

            elif row['debit'] > row['credit']:
                current_balance += balance
                balance_debit += row['debit']
                row['current_balance'] = current_balance
                row['balance_debit'] = balance_debit
                row['balance_type'] = 'D'

            else:
                row['current_balance'] = 0.0
                row['balance_debit'] = 0.0
                row['balance_type'] = ''

            balance = row['balance']
            data.append(row)
        return data

    def query_cost_center_movements(self, cost_center, account_id):
        _query = """
                      SELECT account.name As account_name, account.code As account_code, line.date, journal.name As journal_name, journal.id As journal, SUM(line.debit) AS debit, SUM(line.credit) AS credit, SUM(line.balance) AS balance, move.ref as description, move.name As doc
                      FROM account_move_line line
                       INNER JOIN account_account account ON
                           line.account_id = account.id
                       INNER JOIN account_journal journal ON
                           line.journal_id = journal.id 
                       INNER JOIN account_move move ON
                           line.move_id = move.id
                      WHERE (line.account_id = %(account_id)s)
                          AND (line.cost_Center = %(cost_center)s)
                          AND (line.date >= %(date_from)s)
                          AND (line.date <= %(date_to)s)
                          AND (line.company_id = %(company_id)s)
                          AND (line.move_id_state IN %(move_id_states)s)
                      GROUP BY account.code, account.name, line.date, journal.name, journal.id, move.name, move.ref          
              """

        data = []
        balance = 0.0
        balance_debit = 0.0
        balance_credit = 0.0
        current_balance = 0.0
        args = self._args_query()
        args['account_id'] = account_id
        args['cost_center'] = cost_center
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            balance = row['balance']
            row['balance_debit'] = 0.0  # start
            row['balance_credit'] = 0.0  # start

            if row['credit'] > row['debit']:
                current_balance -= balance
                balance_credit += row['credit']
                row['current_balance'] = current_balance
                row['balance_credit'] = balance_credit
                row['balance_type'] = 'C'

            elif row['debit'] > row['credit']:
                current_balance += balance
                balance_debit += row['debit']
                row['current_balance'] = current_balance
                row['balance_debit'] = balance_debit
                row['balance_type'] = 'D'

            else:
                row['balance_type'] = ''

            balance = row['balance']
            data.append(row)
        return data
        pass

    def _query_cost_center_account_ids(self, cost_center):
        _query = """
                   SELECT account.code As account_id
                   FROM account_move_line line
                     INNER JOIN account_account account ON
                           line.account_id = account.id
                   WHERE (line.cost_center = %(cost_center)s)
                       AND (line.date >= %(date_from)s)
                       AND (line.date <= %(date_to)s)
                       AND (line.company_id = %(company_id)s)
                       AND (line.move_id_state IN %(move_id_states)s)
                   GROUP BY account.code
               """

        data = []
        args = self._args_query()
        args['cost_center'] = cost_center.id
        self.env.cr.execute(_query, args)
        for row in self.env.cr.fetchall():
            data.extend(list(set(row)))
        print(data)
        return data

    def query_fiscal_movements(self, fiscal_plan):
        _query = """
                        SELECT account.name As account_name, account.code As account_code, line.date, journal.name As journal_name, journal.id As journal, SUM(line.debit) AS debit, SUM(line.credit) AS credit, SUM(line.balance) AS balance, move.ref as description, move.name As doc
                        FROM account_move_line line
                         INNER JOIN account_account account ON
                             line.account_id = account.id
                         INNER JOIN account_journal journal ON
                             line.journal_id = journal.id 
                         INNER JOIN account_move move ON
                             line.move_id = move.id
                        WHERE (line.fiscal_plan = %(fiscal_plan)s)
                            AND (line.date >= %(date_from)s)
                            AND (line.date <= %(date_to)s)
                            AND (line.company_id = %(company_id)s)
                            AND (line.move_id_state IN %(move_id_states)s)
                        GROUP BY account.name, account.code, line.date, journal.name, journal.id, move.name, move.ref
                    """
        args = self._args_query()
        args['fiscal_plan'] = fiscal_plan.id
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            print(row)

    def query_cash_flow_movements(self, cash_flow):
        pass

    def query_iva_movements(self, iva_plan):
        pass

    def get_account_move_line(self, account=None):
        return self.query_account_movements(account or self.account_id.id)

    def get_cost_center_move_line(self, cost_center=None, account=None):
        return self.query_cost_center_movements(cost_center, account)

    def get_other_move_line(self):
        if self.filter_by == 'cost_center':
            if not self.by_account:
                for cost_center in self.env['account.cost.center'].search([]):
                    pass
            return self._query_cost_center_account_ids(self.cost_center)
        elif self.filter_by == 'fiscal_plan':
            self.query_fiscal_movements(self.fiscal_plan)

    def amount_format(self, value):
        return formatLang(self.env, abs(value))

    def print_report(self):
        self.get_other_move_line()
        return self.env.ref('es_account_report_ao.action_report_account_extract_ao').report_action(self)
