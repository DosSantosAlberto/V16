from datetime import datetime
from odoo.tools.misc import formatLang
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class TreasuryBoxSession(models.Model):
    _name = 'treasury.box.session'
    _description = 'Treasury Session'

    name = fields.Char('Reference')
    start_balance = fields.Float(string='Starting Balance', )
    end_balance = fields.Float(string='Ending Balance')
    start_date = fields.Datetime(string='Start date')
    end_date = fields.Datetime(string='End date')
    journals = fields.Many2many(comodel_name='account.journal', string='Journals')
    state = fields.Selection([('opened', 'Opened'), ('closed', 'Closed')], default='opened')
    box = fields.Many2one(comodel_name='treasury.box', string='Box')
    session_lines = fields.One2many(comodel_name='treasury.box.session.line', inverse_name='session', string='Lines')

    def unlink(self):
        for session in self:
            if session.state == 'opened':
                raise ValidationError(_('You can not delete this box with opened session'))
            if session.session_lines:
                raise ValidationError(_('You can not delete this box with transitions record'))

    @api.model_create_multi
    def create(self, values):
        result = super(TreasuryBoxSession, self).create(values)
        sequence = self.env['ir.sequence'].next_by_code('es.treasury.session') or '/'
        result.name = '%s' % sequence
        return result

    def close(self):
        for session in self:
            total = 0.0
            box = session.box
            session.state = 'closed'
            session.end_date = datetime.today()
            for journal in self.journals:
                journal_data = box.get_current_balance(journal)
                total += journal_data['account_balance']
            session.end_balance = total
            box.session_user_name = ""
            box.state = 'closed'
            box.date = session.end_date
            session.fill_session_line(box.journals.ids)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def get_account_move(self, move_name):
        move = self.env['account.move'].search([('name', '=', move_name)])
        return move

    def fill_session_line(self, journal_ids):
        lines = [(5, 0, 0)]
        payments = self.env['account.payment'].search(
            [('date_create', '>=', self.start_date), ('date_create', '<=', self.end_date),
             ('create_uid', '=', self.create_uid.id), ('journal_id', 'in', journal_ids)])

        treasury_payments = self.env['treasury.cash.flow'].search(
            [('date_create', '>=', self.start_date), ('date_create', '<=', self.end_date),
             ('create_uid', '=', self.env.user.id), ('journal_id', 'in', journal_ids)])
        for payment in payments:
            if payment.state not in ['draft', 'cancel']:
                # move_id = self.get_account_move(payment.move_name)
                payments_values = {
                    'move_id': payment.move_id.id,
                    'payment': payment.id,
                    'journal': payment.journal_id.id,
                    'amount': payment.amount,
                    'communication': payment.ref,
                    'balance': payment.later_balance,
                    'payment_type': payment.payment_type,
                    'partner_id': payment.partner_id.id,
                    'date': payment.create_date,
                    'session': self.id,
                    'currency_id': payment.currency_id.id
                }
                lines.append((0, 0, payments_values))

        for res in treasury_payments:
            if res.type:
                payments_values = {
                    'move_id': res.move_id.id,
                    'journal': res.journal_id.id,
                    'amount': res.amount,
                    'communication': res.name or res.communication,
                    'balance': res.later_balance,
                    'payment_type': res.type,
                    'partner_id': res.partner_id.id,
                    'employee_id': res.employee_id.id,
                    'debtor': res.debtor.id,
                    'creditor': res.creditor.id,
                    'status': res.status.id,
                    'date': res.create_date,
                    'session': self.id,
                    'currency_id': res.currency_id.id,
                }
                lines.append((0, 0, payments_values))
        self.session_lines = lines

    @staticmethod
    def get_actual_balance(journal_id):
        journal_data = journal_id.get_journal_dashboard_datas()
        return journal_data['account_balance']

    def get_post_balance(self, journal_id, move_id, type):
        move_line = self.env['account.move.line']
        if type == 'inbound':
            move_line = self.env['account.move.line'].search(
                [('journal_id', '=', journal_id.id), ('move_id', '=', move_id.id), ('debit', '>', 0.0)])
        elif type == 'outbound':
            move_line = self.env['account.move.line'].search(
                [('journal_id', '=', journal_id.id), ('move_id', '=', move_id.id), ('credit', '>', 0.0)])
        return move_line

    def amount_format(self, amount):
        return formatLang(self.env, amount)


class TreasuryBoxSessionLine(models.Model):
    _name = 'treasury.box.session.line'
    _description = 'name'
    _order = 'date asc, payment_type desc'

    session = fields.Many2one(comodel_name='treasury.box.session', string='Session')
    payment = fields.Many2one(comodel_name='account.payment', string='Doc')
    journal = fields.Many2one(comodel_name='account.journal', string='Journal')
    date = fields.Datetime(string='Date')
    release_date = fields.Date(string='Release Date', related='move_id.date')
    amount = fields.Monetary(string='Amount')
    balance = fields.Monetary(string='Balance')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    currency_id = fields.Many2one('res.currency', string='Currency', required=False,
                                  default=lambda self: self.env.user.company_id.currency_id)
    payment_type = fields.Selection([('outbound', 'Send Money'), ('inbound', 'Receive Money')], string='Payment Type')
    move_id = fields.Many2one(comodel_name='account.move')
    communication = fields.Char(string='Memo')
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee")
    status = fields.Many2one(comodel_name="es.entity", string='Status', domain=[('is_status', '!=', False)])
    debtor = fields.Many2one(comodel_name="es.entity", string='Debtor', domain=[('debtor', '!=', False)])
    creditor = fields.Many2one(comodel_name="es.entity", string='Creditor', domain=[('creditor', '!=', False)])
