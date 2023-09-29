from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

out_balance = 0.0


class TreasuryCashFlow(models.Model):
    _name = 'treasury.cash.flow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Treasury Cash Flow'
    _order = "date desc, name desc"

    name = fields.Char(string="Name")
    type = fields.Selection([
        ('outbound', 'Out'), ('inbound', 'In')
    ], string="Operation Type")
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('status', 'Status'),
        ('gb', 'Governing Body'),
        ('employee', 'Employee'),
        ('debtor', 'Other Debtors'),
        ('creditor', 'Other creditors'),
        ('other', 'Other'),
    ], string="Entity Type")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ], string="State", default='draft')
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal')
    destination_journal_id = fields.Many2one(comodel_name='account.journal', string='Journal')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    other_partner = fields.Char(string='Responsible')
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee")
    date = fields.Date(string="Payment Date", default=fields.Date.today)
    amount = fields.Monetary(string='Payment Amount', required=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company",
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', required=False,
                                  default=lambda self: self.env.user.company_id.currency_id)
    rubric_id = fields.Many2one(comodel_name='treasury.rubric', string='Rubric', ondelete='restrict')
    communication = fields.Text(string='Memo')
    journal_type = fields.Char(string='Journal Type')
    destination_journal_type = fields.Char('Destination Journal Type')
    move_id = fields.Many2one(comodel_name='account.move', string='Journal Entries')
    has_cost_center = fields.Boolean(related='company_id.treasury_cost_center')
    is_deposit = fields.Boolean(string='Is Deposit', default=False)
    is_take_money = fields.Boolean(string='Is Take Money', default=False)
    is_cash_transfer = fields.Boolean(string='Is Cash Transfer', default=False)
    is_bank_transfer = fields.Boolean(string='Is Bank Transfer', default=False)
    is_inbound = fields.Boolean(string='Is Inbound')
    is_outbound = fields.Boolean(string='Is Outbound')
    cost_center = fields.Many2one(comodel_name='account.cost.center', string='Cost Center')
    ref = fields.Char(string="Ref")
    origin = fields.Char(string="Origin")
    date_create = fields.Datetime('Onw Create Date')
    date_update = fields.Datetime('Onw Update Date')
    later_balance = fields.Monetary(string='Later Balance')
    customer = fields.Many2one(comodel_name='res.partner', string='Customer')
    vendor = fields.Many2one(comodel_name='res.partner', string='Vendor')
    status = fields.Many2one(comodel_name="es.entity", string='Status', domain=[('is_status', '!=', False)])
    debtor = fields.Many2one(comodel_name="es.entity", string='Debtor', domain=[('debtor', '!=', False)])
    creditor = fields.Many2one(comodel_name="es.entity", string='Creditor', domain=[('creditor', '!=', False)])

    @api.onchange('partner_type')
    def onchange_partner_type(self):
        if self.partner_type in ['customer']:
            self.vendor = False
            self.partner_id = False
        elif self.partner_type in ['supplier']:
            self.customer = False
            self.partner_id = False
        else:
            self.partner_id = False
            self.vendor = False
            self.customer = False

    @api.onchange('customer')
    def onchange_customer(self):
        if self.partner_type in ['customer']:
            self.partner_id = self.customer

    @api.onchange('vendor')
    def onchange_vendor(self):
        if self.partner_type in ['supplier']:
            self.partner_id = self.vendor

    @api.model_create_multi
    def create(self, vals_list):
        result = super(TreasuryCashFlow, self).create(vals_list)
        sequence = ''
        if result.type == 'outbound' and result.journal_id.type == 'cash':
            sequence = self.env['ir.sequence'].next_by_code('hs.treasury.cash.out') or '/'
        if result.type == 'inbound' and result.journal_id.type == 'cash':
            sequence = self.env['ir.sequence'].next_by_code('hs.treasury.cash.in') or '/'
        if result.type == 'outbound' and result.journal_id.type == 'bank':
            sequence = self.env['ir.sequence'].next_by_code('hs.treasury.bank.out') or '/'
        if result.type == 'inbound' and result.journal_id.type == 'bank':
            sequence = self.env['ir.sequence'].next_by_code('hs.treasury.bank.in') or '/'
        result.journal_type = result.journal_id.type
        result.destination_journal_type = result.destination_journal_id.type
        result.name = '%s' % sequence if result.type in ['outbound', 'inbound'] else result.name
        result.date_create = datetime.now()
        result.date_update = datetime.now()
        return result

    def write(self, values):
        values['date_update'] = datetime.now()
        return super(TreasuryCashFlow, self).write(values)

    def post(self):
        self.journal_entries()
        self.state = 'posted'

    def action_draft(self):
        moves = self.mapped('move_id')
        moves.unlink()
        self.state = 'draft'

    def action_cancel(self):
        reverse_entry = self.env["account.move.reversal"].create({
            'move_is': [(6, 0, self.move_id.ids)],
            'date_mode': 'custom',
            'journal_id': self.journal_id.id,
            'date': fields.Date.today
        })
        reverse_entry.reverse_moves()
        # moves = self.mapped('move_id')
        # moves.filtered(lambda l: l.state == 'posted').button_cancel()
        self.state = 'cancelled'

    def get_later_balance(self, type):
        global out_balance
        later_balance = 0.0
        if type == 'outbound':
            later_balance = self.get_balance() - self.amount
            out_balance = later_balance
        elif type == 'inbound':
            if out_balance == 0.0:
                later_balance = self.get_balance() + self.amount
            else:
                later_balance = out_balance + self.amount
        return later_balance

    def get_balance(self):
        opened_session = self.env['treasury.box.session'].search(
            [('state', '=', 'opened'), ('create_uid', '=', self.env.user.id)])
        total = 0.0
        for session in opened_session:
            total = 0.0
            for journal in session.journals:
                for j in journal.default_account_id:
                    total += j.current_balance
                # journal_data = journal.get_journal_dashboard_datas()
                # total += journal_data['amount_balance']
        return total

    @staticmethod
    def _prepare_journal_entries(res_id, account_id, account_journal_id):
        # @author: Hermenegildo Mulonga
        """
            res_id: object
            account_id: int
            account_journal_id: int
        """
        return {
            'date': res_id.date,
            'journal_id': res_id.journal_id.id,
            'ref': res_id.origin or res_id.name,
            'narration': res_id.communication,
            'line_ids': [(0, 0, {
                'account_id': account_id,
                'journal_id': res_id.journal_id.id,
                'date': res_id.date,
                'partner_id': res_id.partner_id.id or res_id.employee_id.address_home_id.id,
                'name': res_id.partner_id.name or res_id.employee_id.name or '/',
                'debit': res_id.amount if res_id.type == 'outbound' else 0.0,
                'credit': res_id.amount if res_id.type == 'inbound' else 0.0,
            }),
                         (0, 0, {
                             'account_id': account_journal_id,
                             'journal_id': res_id.journal_id.id,
                             'date': res_id.date,
                             'partner_id': res_id.partner_id.id or res_id.employee_id.address_home_id.id,
                             'name': res_id.communication or '/',
                             'debit': res_id.amount if res_id.type == 'inbound' else 0.0,
                             'credit': res_id.amount if res_id.type == 'outbound' else 0.0,
                         })]

        }

    def journal_entries(self):

        if self.type in ['outbound', 'inbound']:
            move_values = self._prepare_journal_entries(self, self.get_account(), self.journal_id.default_account_id.id)
            move = self.env['account.move'].create(move_values)
            self.move_id = move
            move.action_post()  # Posting to Accounting
        elif self.is_take_money:
            outbound = self.env['treasury.cash.flow'].create(self.get_value(self.journal_id.id, 'outbound'))
            inbound = self.env['treasury.cash.flow'].create(self.get_value(self.destination_journal_id.id, 'inbound'))

            if self.company_id.transitory_account:
                # C 43??? (Conta Banco onde o dinheiro saiu) – Movimento de Saída de Valores
                # D 482? (Conta Transitória Banco) - Movimento de Entrada de Valores
                move_out_values = self._prepare_journal_entries(outbound,
                                                                outbound.journal_id.suspense_account_id.id,
                                                                outbound.journal_id.default_account_id.id)

                # D 451? (Conta Caixa onde o dinheiro entrou) - Movimento de Entrada de Valores
                # C 482? (Conta Transitória Banco) - Movimento de Saída de Valores
                move_in_values = self._prepare_journal_entries(inbound,
                                                               outbound.journal_id.suspense_account_id.id,
                                                               inbound.journal_id.default_account_id.id)
                move_out = self.env['account.move'].create(move_out_values)
                move_in = self.env['account.move'].create(move_in_values)
                outbound.move_id = move_out
                outbound.state = 'posted'
                inbound.move_id = move_in
                inbound.state = 'posted'
                move_out.action_post()  # Posting to Accounting
                move_in.action_post()  # Posting to Accounting
        elif self.is_deposit:
            outbound = self.env['treasury.cash.flow'].create(self.get_value(self.journal_id.id, 'outbound'))
            inbound = self.env['treasury.cash.flow'].create(self.get_value(self.destination_journal_id.id, 'inbound'))

            if self.company_id.transitory_account:
                # C 45?? (Conta Caixa onde o dinheiro saiu) – Movimento de Saída de Valores
                # D 482? (Conta Transitória Caixa) - Movimento de Entrada de Valores
                move_out_values = self._prepare_journal_entries(outbound,
                                                                outbound.journal_id.suspense_account_id.id,
                                                                outbound.journal_id.default_account_id.id)

                # D 43??? (Conta Banco onde o dinheiro entrou) – Movimento de Entrada de Valores
                # C 482? (Conta Transitória Caixa) - Movimento de Saída de Valores
                move_in_values = self._prepare_journal_entries(inbound,
                                                               outbound.journal_id.suspense_account_id.id,
                                                               inbound.journal_id.default_account_id.id
                                                               )

                move_out = self.env['account.move'].create(move_out_values)
                move_in = self.env['account.move'].create(move_in_values)
                outbound.move_id = move_out
                outbound.state = 'posted'
                inbound.move_id = move_in
                inbound.state = 'posted'
                move_out.action_post()  # Posting to Accounting
                move_in.action_post()  # Posting to Accounting
        elif self.is_bank_transfer:
            outbound = self.env['treasury.cash.flow'].create(self.get_value(self.journal_id.id, 'outbound'))
            inbound = self.env['treasury.cash.flow'].create(self.get_value(self.destination_journal_id.id, 'inbound'))

            if self.company_id.transitory_account:
                # C 43??? (Conta Banco onde o dinheiro saiu) – Movimento de Saída de Valores
                # D 482? (Conta Transitória Banco) - Movimento de Entrada de Valores
                move_out_values = self._prepare_journal_entries(outbound,
                                                                outbound.journal_id.suspense_account_id.id,
                                                                outbound.journal_id.default_account_id.id)

                # D 43??? (Conta Banco onde o dinheiro entrou) - Movimento de Entrada de Valores
                # C 482? (Conta Transitória Banco) - Movimento de Saída de Valores
                move_in_values = self._prepare_journal_entries(inbound,
                                                               outbound.journal_id.suspense_account_id.id,
                                                               inbound.journal_id.default_account_id.id
                                                               )
                move_out = self.env['account.move'].create(move_out_values)
                move_in = self.env['account.move'].create(move_in_values)
                outbound.move_id = move_out
                outbound.state = 'posted'
                inbound.move_id = move_in
                inbound.state = 'posted'
                move_out.action_post()  # Posting to Accounting
                move_in.action_post()  # Posting to Accounting
        elif self.is_cash_transfer:
            outbound = self.env['treasury.cash.flow'].create(self.get_value(self.journal_id.id, 'outbound'))
            inbound = self.env['treasury.cash.flow'].create(self.get_value(self.destination_journal_id.id, 'inbound'))

            if self.company_id.transitory_account:
                # C 45??? (Conta caixa onde o dinheiro saiu) – Movimento de Saída de Valores
                # D 482? (Conta Transitória caixa) - Movimento de Entrada de Valores
                move_out_values = self._prepare_journal_entries(outbound,
                                                                outbound.journal_id.suspense_account_id.id,
                                                                outbound.journal_id.default_account_id.id)

                # D 45??? (Conta caixa onde o dinheiro entrou) - Movimento de Entrada de Valores
                # C 482? (Conta Transitória caixa) - Movimento de Saída de Valores
                move_in_values = self._prepare_journal_entries(inbound,
                                                               outbound.journal_id.suspense_account_id.id,
                                                               inbound.journal_id.default_account_id.id

                                                               )
                move_out = self.env['account.move'].create(move_out_values)
                move_in = self.env['account.move'].create(move_in_values)
                outbound.move_id = move_out
                outbound.state = 'posted'
                inbound.move_id = move_in
                inbound.state = 'posted'
                move_out.action_post()  # Posting to Accounting
                move_in.action_post()  # Posting to Accounting
        if self.is_inbound:
            self.later_balance = self.get_balance()
        if self.is_outbound:
            self.later_balance = self.get_balance()

    def get_value(self, journal_id, type):
        return {
            'name': self.name,
            'partner_type': self.partner_type,
            'other_partner': self.other_partner,
            'employee_id': self.employee_id.id or False,
            'partner_id': self.partner_id.id or False,
            'origin': self.ref,
            'journal_id': journal_id,
            'type': type,
            'amount': self.amount,
            'date': self.date,
            'later_balance': self.get_later_balance(type),
            'communication': self.communication
        }

    def get_account(self):
        if not self.rubric_id:
            if self.partner_type in ['employee', 'gb']:
                if self.employee_id.employee_type != 'o':  # is employee?
                    code = self.company_id.treasury_prefix_account_employee
                    return self._check_account(code)
                elif self.employee_id.employee_type == 'o':  # is governing body?
                    code = self.company_id.treasury_prefix_account_social
                    return self._check_account(code)
            elif self.partner_type == 'debtor':
                code = self.debtor.account_id.code or self.company_id.treasury_prefix_account_debtor
                return self._check_account(code)
            elif self.partner_type == 'creditor':
                code = self.creditor.account_id.code or self.company_id.treasury_prefix_account_creditor
                return self._check_account(code)
            elif self.partner_type == 'status':
                code = self.status.account_id.code or self.company_id.treasury_prefix_account_status
                return self._check_account(code)
            elif self.partner_type == 'customer':
                return self.partner_id.property_account_receivable_id.id
            elif self.partner_type == 'supplier':
                return self.partner_id.property_account_payable_id.id
        else:
            # Returns the account of rubric if  rubric field is filled
            return self._check_account(self.rubric_id.account_code)
        return False

    def _check_account(self, code):
        acc = self.env['account.account'].search([('code', '=', code.strip()), ('company_id', '=', self.company_id.id)])
        if not acc:
            raise UserError(_("Account %s does not exist in the account plan,\n"
                              " please create the account and try again") % code)
        return acc.id

    @api.constrains('journal_id')
    def _chek_treasury_user(self):
        if self.type in ['outbound', 'inbound']:
            self.check_balance_restriction()
        if self.env.user.has_group('es_treasury.group_treasury_manager') or self.env.user.has_group(
                'es_treasury.group_treasury_treasurer'):
            current_session = self.env['treasury.box.session'].search(
                [('create_uid', '=', self.env.user.id), ('state', '=', 'opened'),
                 ('journals', 'in', self.journal_id.ids)])
            if not current_session:
                raise ValidationError(
                    _('Box closed, please open an box first that have a journal %s !') % self.journal_id.name)
        else:
            raise ValidationError(_('User must be part of the treasury group!'))

    def check_balance_restriction(self):
        if self.type == 'outbound':
            if self.env.user.company_id.restrict_payment_without_balance:
                if self.get_actual_balance(self.journal_id) < self.amount:
                    raise ValidationError(_('Not enough balance in journal, can not make this operation'))

    @staticmethod
    def get_actual_balance(journal_id):
        total = 0.0
        for jornal in journal_id:
            if jornal.default_account_id:
                total += jornal.default_account_id.current_balance
        return total
        # journal_data = journal_id.get_journal_dashboard_datas()
        # return journal_data['amount_balance']

    def unlink(self):
        for res in self:
            if res.state not in ['draft']:
                raise ValidationError(_('You can not delete this record. Please contact the system administrator!'))
        return super(TreasuryCashFlow, self).unlink()
