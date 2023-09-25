from odoo import fields, models, api,_
from odoo.tools.misc import formatLang
from datetime import datetime






class AccountReportTrialBalance(models.TransientModel):
    _name = 'account.report.trial.balance'
    _description = 'Trial Balance Angola'
    _rec_name = 'fiscal_year'

    fiscal_year = fields.Many2one(comodel_name="account.fiscal.year", string="Fiscal Year")
    periods = fields.Many2many(comodel_name="account.fiscal.period", string="Period")
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id, string="Company")
    target_move = fields.Selection([
        ('posted', 'Posted Entries only'),
        ('all', 'All Entries')
    ], string="Accounting Movements", default='posted')
    type = fields.Selection([
        ('general', 'General'),
        ('reason', 'Reason')
    ], default='general', string="Type")

    @api.onchange('fiscal_year')
    def onchange_fiscal_year(self):
        self.date_from = self.fiscal_year.date_from
        self.date_to = self.fiscal_year.date_to
        self.periods = False

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.date_from = False
        self.date_to = False
        self.fiscal_year = False
        self.periods = False

    def _args_query(self):
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'periods': tuple(self.periods.ids),
            'move_id_states': tuple([self.target_move] if self.target_move == 'posted' else ['posted', 'draft'])
        }

    def get_balance_reason(self):
        reason_balance = []
        reason_group = self.env['account.account'].search([('nature', '=', 'R')])
        for reason in reason_group:
            _before_codes = []
            record = self.query_reason_balance(reason.code)
            if record is not None:
                record['name'] = reason.name.upper()
                record['nature'] = reason.nature
                balance = record['balance']
                record['balance_debit'] = balance if balance > 0.0 else 0.0
                record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                reason_balance.append(record)
        return reason_balance

    def get_balance_general(self):
        general_balance = []
        reason_group = self.env['account.account'].search([('nature', '=', 'R')])
        integrator_group = self.env['account.account'].search([('nature', '=', 'I')])
        for reason in reason_group:
            _before_codes = []
            record = self.query_reason_balance(reason.code)
            if record is not None:
                record['name'] = reason.name.upper()
                record['nature'] = reason.nature
                balance = record['balance']
                record['balance_debit'] = balance if balance > 0.0 else 0.0
                record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                general_balance.append(record)
            for integrator in integrator_group:
                if integrator.reason_code == reason.code:

                    # CHECK MOVE LINE WITH INTEGRATOR ACCOUNT (After Clearance)
                    print(integrator.code)
                    record = self.query_account_move(integrator.code)
                    if record is not None:
                        record['name'] = integrator.name
                        record['nature'] = integrator.nature
                        balance = record['balance']
                        record['balance_debit'] = balance if balance > 0.0 else 0.0
                        record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                        general_balance.append(record)

                    # NORMAL CASE
                    record = self.query_integrator_balance(integrator.code)
                    if record:
                        record['name'] = integrator.name
                        record['nature'] = integrator.nature
                        balance = record['balance']
                        record['balance_debit'] = balance if balance > 0.0 else 0.0
                        record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                        general_balance.append(record)

                        accounts = self._get_movement_nature_accounts(integrator.code)
                        for account in accounts:
                            record = self.query_account_move(account.code)
                            if record is not None:
                                record['name'] = account.name
                                record['nature'] = account.nature
                                balance = record['balance']
                                record['balance_debit'] = balance if balance > 0.0 else 0.0
                                record['balance_credit'] = balance * -1 if balance < 0.0 else 0.0
                                general_balance.append(record)
                    else:
                        # _before_codes.append(integrator.code)
                        _count = 0
                        accounts = self._get_parent_integrator(integrator.code)
                        _record = {'code': '', 'debit': 0, 'credit': 0, 'balance_debit': 0, 'balance_credit': 0, }
                        for account in accounts:
                            record = self.query_integrator_balance(account.code)
                            if record is not None:
                                balance = record['balance']
                                _record['debit'] += record['debit']
                                _record['credit'] += record['credit']
                                _record['balance_debit'] += balance if balance > 0.0 else 0.0
                                _record['balance_credit'] += balance * -1 if balance < 0.0 else 0.0
                                _record['code'] = integrator.code
                                _record['name'] = integrator.name
                                _record['nature'] = integrator.nature
                                _count += 1

                        if _count > 0: general_balance.append(_record)
        return general_balance

    def query_reason_balance(self, code):
        _query = """
            SELECT reason_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
            FROM account_move_line 
            WHERE (reason_code = %(reason_code)s)
                AND (date >= %(date_from)s)
                AND (date <= %(date_to)s)
                AND (period IN %(periods)s)
                AND (company_id = %(company_id)s)
                AND (move_id_state IN %(move_id_states)s)
            GROUP BY reason_code
        """
        args = self._args_query()
        args['reason_code'] = code
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            return row
        return None

    def query_integrator_balance(self, code):
        _query = """
            SELECT integrator_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
            FROM account_move_line 
                WHERE (integrator_code = %(integrator_code)s)
                AND (date >= %(date_from)s)
                AND (date <= %(date_to)s)
                AND (period IN %(periods)s)
                AND (company_id = %(company_id)s)
                AND (move_id_state IN %(move_id_states)s) 
            GROUP BY integrator_code
        """
        args = self._args_query()
        args['integrator_code'] = code
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            return row
        return None

    def query_account_move(self, code):
        _query = """
            SELECT account_code AS code, SUM(debit) AS debit, SUM(credit) AS credit, SUM(balance)AS balance 
            FROM account_move_line 
                WHERE (account_code = %(account_code)s)
                AND (date >= %(date_from)s)
                AND (date <= %(date_to)s)
                AND (period IN %(periods)s)
                AND (company_id = %(company_id)s)
                AND (move_id_state IN %(move_id_states)s)  
            GROUP BY account_code
        """
        args = self._args_query()
        args['account_code'] = code
        self.env.cr.execute(_query, args)
        for row in self.env.cr.dictfetchall():
            return row
        return None

    def _get_movement_nature_accounts(self, integrator_code):
        accounts = self.env['account.account'].search([('nature', '=', 'M'), ('integrator_code', '=', integrator_code)])
        # self.env.user.has_group('base.group_system')
        return accounts

    def _get_parent_integrator(self, code):
        accounts = self.env['account.account'].search([('nature', '=', 'I'), ('integrator_code', '=', code)])
        return accounts

    def _get_periods(self, code):
        accounts = self.env['account.fiscal.period'].search([('nature', '=', 'I'), ('integrator_code', '=', code)])
        return accounts

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    def name_balance(self):

        name = set()
        d2 = self.date_from.strftime('%B')
        d3 = self.date_to.strftime('%B')

        for rec in self:
            for re in rec.periods:
                name.add(re.period)
        if "0" in name and "12" not in name and "13" not in name and "14" not in name and "15" not in name:
            return f'{d2, " / ", d3}'.replace(',', "")
        if "12" in name and "13" in name and "0" not in name and "15" not in name and "14" not in name:
            return f'{d2, " / ", "Reg"}'.replace(',', "")
        if "12" in name and "13" in name and "14" in name and "0" not in name and "15" not in name:
            return f'{d2, "/", "Fim"}'.replace(',', "")
        if "12" in name and "13" in name and "0" in name and "14" not in name and "15" not in name:
            return "Abertura / Regularização"
        if "0" in name and "12" in name and "13" in name and "14" in name and "15" in name:
            return "Abertura / Fim"
        else:
            if re.period == "12":
                return "Entradas Comuns"
            if re.period == "13":
                return "Entradas de Regularização"
            if re.period == "14":
                return "Liberação"
            if re.period == "15":
                return "Fechamento"

    def print_pdf(self):
        return self.env.ref('es_account_report_ao.action_report_trial_balance_ao').report_action(self)
