from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


def employee_account_index(employee_type):
    if employee_type != 'o':  # is employee_type?
        return '2'
    return '1'  # is governing body?


class AccountPayment(models.Model):
    _name = 'account.payment.salary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Salary Payment Angola"

    name = fields.Char(string="Name")
    ref = fields.Char(string="Reference")
    communication = fields.Char(string="Description")
    date = fields.Date(string="Date", default=fields.Date.today)
    hr_payment = fields.Many2one(comodel_name="hr.payment", string='Salary Payment Order')
    amount = fields.Monetary(string='Amount to Pay', required=True)
    lines = fields.One2many('account.payment.hr', 'salary_payment', 'Payment Line')
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal')
    move_id = fields.Many2one(comodel_name="account.move", string="Move")
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
        ('employee', 'Employee'),
    ], default='customer', tracking=True, required=True)
    payment_method = fields.Selection([
        ('transfer', 'Transference'),
        ('deposit', 'Deposit'),
        ('cash', 'Cash'),
    ], default='transfer', tracking=True, required=True)
    slip_amount = fields.Monetary(string='Salary Total', compute="_compute_irt_amount")
    hr_irt_amount = fields.Monetary(string='IRT Total', compute="_compute_irt_amount")
    hr_ss_amount = fields.Monetary(string='SS Total', compute="_compute_irt_amount")
    currency_id = fields.Many2one('res.currency', string='Currency', required=False,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_split = fields.Selection([
        ('automated', 'Automatic'), ('manual', 'Manual'),
    ], string="Division", default="automated")
    state = fields.Selection([
        ('draft', 'Draft'), ('posted', 'Posted'),
    ], string="State", default="draft")
    payment_type = fields.Selection([
        ('outbound', 'Out'), ('inbound', 'In')
    ], string="Operation Type", default='outbound')
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id)
    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")

    @api.depends('hr_payment.lines')
    def _compute_irt_amount(self):
        for res in self:
            res.hr_irt_amount = sum([line.irt_amount for line in res.hr_payment.lines])
            res.hr_ss_amount = sum([line.ss_amount for line in res.hr_payment.lines])
            res.slip_amount = sum([line.amount for line in res.hr_payment.lines])

    @api.onchange('hr_payment')
    def onchange_hr_payment(self):
        hr_payment_lines = [(5, 0, 0)]
        for line in self.hr_payment.lines:
            hr_payment_lines.append((0, 0, {
                'name': line.employee_id.name,
                'employee_type': line.employee_id.employee_type,
                'amount': line.amount,
                'irt_amount': line.irt_amount,
                'ss_amount': line.ss_amount,
            }))
        self.lines = hr_payment_lines

    def hr_payment_post(self):
        for res in self:
            if res.journal_id.type not in ['bank', 'cash']:
                raise ValidationError(_("Diario de Pagamento deve ser Banco ou Numerario"))
            if res.amount > res.slip_amount:
                raise ValidationError(_("VALOR DO PAGAMENTO NAO DEVE SER SUPERIOR AO TOTAL  A PAGAR"))

            if res.payment_split == 'automated':
                if res.amount == res.slip_amount:
                    for line in res.lines:
                        line.amount_paid = line.amount
                    for hr_line in res.hr_payment.lines:
                        hr_line.amount_paid = hr_line.amount

                    res.hr_payment.amount_paid = res.amount
                    res.hr_payment.state = 'paid'
                    res.hr_payment.payslip_run_id.payment_state = 'paid'
                else:
                    _rate = res.amount / res.slip_amount
                    for line in res.lines:
                        line.amount_paid = line.amount * _rate
                    for hr_line in res.hr_payment.lines:
                        hr_line.amount_paid = hr_line.amount * _rate

                    res.hr_payment.amount_paid += res.amount
                    if res.hr_payment.amount_paid == res.slip_amount:
                        res.hr_payment.state = 'paid'
                        res.hr_payment.payslip_run_id.payment_state = 'paid'
            else:
                for line in res.lines:
                    for hr_line in res.hr_payment.lines:
                        if line.external_id == hr_line.id:
                            hr_line.amount_paid = line.amount_paid

                total_paid = sum([line.amount_paid for line in self.lines])
                res.amount = total_paid
                res.hr_payment.amount_paid += total_paid
                if res.hr_payment.amount_paid == res.slip_amount:
                    res.hr_payment.state = 'paid'
                    res.hr_payment.payslip_run_id.payment_state = 'paid'

            move = self.env['account.move'].create(self.hr_entry_journal_payment(res))
            move._post()
            res.write({'state': 'posted', 'move_id': move.id})

    def _check_account(self, account_code, company_id):
        account = self.env['account.account'].search([('code', '=', account_code), ('company_id', '=', company_id.id)])
        if not account:
            raise ValidationError("Account %s does not exist in the account plan,\n"
                                  " please create the account and try again" % account_code)
        return account

    def hr_entry_journal_payment(self, res):
        lines = []
        account_move_dict = {
            'narration': res.communication,
            'ref': res.name,
            'journal_id': res.journal_id.id,
            'date': res.date,
        }
        if res.hr_payment.payslip_run_id.structure_type_id.type == 'employee':
            lines.append(self.move_line_salary())
            lines.extend(self.charges_payable_debit(['3', '4']))
            lines.extend(self.charges_payable_credit(['3431', '34951']))
            lines.extend(self.personnel_remuneration(['employee', 'o']))
        elif res.hr_payment.payslip_run_id.structure_type_id.type == 'worker':
            lines.extend(self.move_debit_worker_payroll())
            lines.extend(self.move_credit_worker_payroll())
        account_move_dict['line_ids'] = lines
        return account_move_dict

    def move_line_salary(self):
        for res in self:
            return (0, 0, {
                'name': res.journal_id.name,
                'partner_id': False,
                'account_id': res.journal_id.default_account_id.id,
                'journal_id': res.journal_id.id,
                'date': res.date,
                'cost_center': res.cost_center.id if res.cost_center else False,
                'debit': 0.0,
                'credit': res.amount,
            })

    def charges_payable_debit(self, index_accounts):
        """
       :param index_accounts: should be (3) or (4)
        3 = SS, 4 = IRT
        :param hr_payment:
        :return:
        """
        for res in self:
            lines = []
            _proportion_amount = res.amount / res.slip_amount
            _proportion_ss = _proportion_amount * res.hr_ss_amount
            _proportion_irt = _proportion_amount * res.hr_irt_amount
            for index in index_accounts:
                account = "%s%s" % (res.company_id.prefix_account_charges_payable, index)
                account = self._check_account(account, res.company_id)
                lines.append((0, 0, {
                    'name': 'SS' if index == '3' else 'IRT',
                    'partner_id': False,
                    'account_id': account.id,
                    'journal_id': res.journal_id.id,
                    'date': res.date,
                    'cost_center': res.cost_center.id if res.cost_center else False,
                    'credit': 0.0,
                    'debit': _proportion_ss if index == '3' else _proportion_irt,
                }))
            return lines

    def charges_payable_credit(self, account_codes):
        """
       :param account_codes: should be (3431) or (34951)
        34951  = SS, 3431 = IRT
        :param hr_payment:
        :return:
        """
        for res in self:
            lines = []
            _proportion_amount = res.amount / res.slip_amount
            _proportion_ss = _proportion_amount * res.hr_ss_amount
            _proportion_irt = _proportion_amount * res.hr_irt_amount
            for code in account_codes:
                account = "%s" % code
                account = res._check_account(account, res.company_id)
                lines.append((0, 0, {
                    'name': 'SS' if code == '34951' else 'IRT',
                    'partner_id': False,
                    'account_id': account.id,
                    'journal_id': res.journal_id.id,
                    'date': res.date,
                    'cost_center': res.cost_center.id if res.cost_center else False,
                    'credit': _proportion_ss if code == '34951' else _proportion_irt,
                    'debit': 0.0
                }))
            return lines

    def personnel_remuneration(self, index_accounts):
        """
        :param index_accounts: should be (e) or (o)
        e = employee(36121), o = governing body(36111)
        :param hr_payment:
        :return:
        """
        for res in self:
            lines = []
            for index in index_accounts:
                if index in set([line.employee_type for line in res.lines]):
                    account = "%s%s" % (
                        res.company_id.prefix_account_personnel_remuneration, employee_account_index(index))
                    account = res._check_account(account + '1', res.company_id)
                    lines.append((0, 0, {
                        'name': 'Salario Liquido',
                        'partner_id': False,
                        'account_id': account.id,
                        'journal_id': res.journal_id.id,
                        'date': res.date,
                        'cost_center': res.cost_center.id if res.cost_center else False,
                        'credit': 0.0,
                        'debit': res.employee_salary() if index != 'o' else res.governing_body_salary() or 0.0,
                    }))
            return lines

    def move_credit_worker_payroll(self):
        for res in self:
            account = res._check_account('3432', res.company_id)
            _proportion_amount = res.amount / res.slip_amount
            _proportion_irt = _proportion_amount * res.hr_irt_amount

            return [(0, 0, {
                'name': "Remuneracao Liquida",
                'partner_id': False,
                'account_id': res.journal_id.default_account_id.id,
                'journal_id': res.journal_id.id,
                'date': res.date,
                'cost_center': res.cost_center.id if res.cost_center else False,
                'debit': 0.0,
                'credit': res.amount,
            }), (0, 0, {
                'name': "IRT",
                'partner_id': False,
                'account_id': account.id,
                'journal_id': res.journal_id.id,
                'date': res.date,
                'cost_center': res.cost_center.id if res.cost_center else False,
                'debit': 0.0,
                'credit': _proportion_irt,
            })]

    def move_debit_worker_payroll(self):
        for res in self:
            _proportion_amount = res.amount / res.slip_amount
            _proportion_irt = _proportion_amount * res.hr_irt_amount

            return [(0, 0, {
                'name': "Remuneracao Liquida",
                'partner_id': False,
                'account_id': res._check_account(res.company_id.prefix_account_worker_net_amount,
                                                 res.company_id).id,
                'journal_id': res.journal_id.id,
                'date': res.date,
                'cost_center': res.cost_center.id if res.cost_center else False,
                'debit': res.amount,
                'credit': 0.0,
            }), (0, 0, {
                'name': "IRT",
                'partner_id': False,
                'account_id': res._check_account(res.company_id.prefix_account_worker_irt, res.company_id).id,
                'journal_id': res.journal_id.id,
                'date': res.date,
                'cost_center': res.cost_center.id if res.cost_center else False,
                'debit': _proportion_irt,
                'credit': 0.0,
            })]

    def employee_salary(self):
        return sum([line.amount for line in self.lines if line.employee_type == 'employee'])

    def governing_body_salary(self):
        return sum([line.amount for line in self.lines if line.employee_type == 'o'])

    def action_draft(self):
        pass


class AccountPaymentHr(models.Model):
    _name = 'account.payment.hr'
    _description = 'Hr Payment'

    salary_payment = fields.Many2one(comodel_name="account.payment.salary")
    name = fields.Char(string="Name")
    employee_type = fields.Char(strin="Employee Type")
    external_id = fields.Integer(string="Ext Id")
    amount = fields.Float(string="Processed Amount")
    amount_paid = fields.Float(string="Amount Paid")
    amount_debt = fields.Float(string="Difference", compute='_amount_balance')
    irt_amount = fields.Float(string="IRT Amount")
    ss_amount = fields.Float(string="SS Amount")
    payment_split = fields.Selection([
        ('automated', 'Automatic'), ('manual', 'Manual'),
    ], string="Division", related='salary_payment.payment_split')
    balance = fields.Float(string="Balance", compute='_amount_balance')
    obs = fields.Char(string='obs')

    @api.depends('amount', 'amount_paid')
    def _amount_balance(self):
        for rec in self:
            rec.balance = rec.amount_paid - rec.amount if rec.amount_paid >= rec.amount else 0.0
            rec.amount_debt = rec.amount - rec.amount_paid if rec.amount_paid <= rec.amount else 0.0
