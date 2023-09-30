from odoo import models, api, _, fields
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    treasury_balance = fields.Monetary('Balance Treasury')
    date_create = fields.Datetime('Onw Create Date')
    date_update = fields.Datetime('Onw Update Date')
    later_balance = fields.Monetary(string='Later Balance')

    @api.model_create_multi
    def create(self, vals):
        result = super(AccountPayment, self).create(vals)
        result.date_create = datetime.now()
        result.date_update = datetime.now()
        result.later_balance = self.get_actual_balance()
        return result

    def get_later_balance(self):
        later_balance = self.get_actual_balance()
        return later_balance

    def action_post(self):
        super(AccountPayment, self).action_post()
        self.treasury_balance = self.get_later_balance()

    def get_actual_balance(self):
        opened_session = self.env['treasury.box.session'].search(
            [('state', '=', 'opened'), ('create_uid', '=', self.env.user.id)])
        total = 0.0
        for session in opened_session:
            for journal in session.journals:
                total += journal.default_account_id.current_balance
                # print(journal.get_journal_dashboard_datas())
                # journal_data = journal.get_journal_dashboard_datas()
                # total += journal_data['amount_balance']
        return total

    def write(self, values):
        values['date_update'] = datetime.now()
        values['later_balance'] = self.get_later_balance()
        return super(AccountPayment, self).write(values)

    @api.constrains('amount')
    def _chek_treasury_user(self):
        if self.payment_type in ['outbound', 'inbound']:
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

    @staticmethod
    def get_journal_actual_balance(journal_id):
        total = 0.0
        for jornal in journal_id:
            if jornal.default_account_id:
                total += jornal.default_account_id.current_balance
        return total

    def check_balance_restriction(self):
        if self.payment_type == 'outbound':
            if self.env.user.company_id.restrict_payment_without_balance:
                if self.get_journal_actual_balance(self.journal_id) < self.amount:
                    raise ValidationError(_('Not enough balance in this journal, can not make this operation'))
