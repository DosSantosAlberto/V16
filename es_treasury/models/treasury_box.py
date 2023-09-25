from odoo import fields, models, api, _
from datetime import datetime, date, time
from . import es_utils as util
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import formatLang


class TreasuryBox(models.Model):
    _name = 'treasury.box'
    _description = 'Treasury Box'

    def _get_current_session_user(self):
        for box in self:
            box.current_session_user = box.env.uid
            box.current_user_id = box.env.user

    name = fields.Char('Reference')
    start_balance = fields.Float(string='Starting Balance')
    end_balance = fields.Float(string='Ending Balance')
    date = fields.Date(string='Date', default=fields.Date.today)
    journals = fields.Many2many(comodel_name='account.journal', string='Journals')
    state = fields.Selection([('opened', 'Opened'), ('closed', 'Closed')], default='closed')
    session_user = fields.Integer(string='Session user')
    current_session_user = fields.Integer(compute="_get_current_session_user", string='current session user')
    session_user_name = fields.Char('Session user name')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda l: l.env.user.company_id)
    show_on_panel = fields.Boolean('Show on Panel', default=True)
    current_user_id = fields.Many2one(comodel_name="res.users", string="User", compute="_get_current_session_user")

    @staticmethod
    def get_current_balance(journal):
        last_balance = current_balance = 0.0
        last_statement = journal._get_last_bank_statement(domain=[('move_id.state', '=', 'posted')])
        last_balance = last_statement.balance_end
        has_at_least_one_statement = bool(last_statement)
        bank_account_balance, nb_lines_bank_account_balance = journal._get_journal_bank_account_balance(
            domain=[('parent_state', '=', 'posted')])
        last_balance = last_balance
        current_balance = bank_account_balance
        return {
            'account_balance': current_balance,
            'last_balance': last_balance,
        }

    def button_close_box(self):
        total = 0.0
        for box in self:
            session = box.env['treasury.box.session'].search([
                ('state', '=', 'opened'),
                ('create_uid', '=', self.env.user.id),
                ('box', '=', box.id)
            ])
            for journal in self.journals:
                journal_data = box.get_current_balance(journal)
                total += journal_data['account_balance']
            box.end_balance = total
            if session:
                box.state = 'closed'
                session.close()
                return self.env.ref('es_treasury.report_close_box').report_action(session)

    def button_open_box(self):
        total = 0.0
        for box in self:
            box.check_information(box)
            box.state = 'opened'
            box.session_user = box.env.user.id
            box.session_user_name = box.env.user.name
            session = box.env['treasury.box.session']
            for journal in self.journals:
                journal_data = box.get_current_balance(journal)
                total += journal_data['account_balance']
            box.start_balance = total
            res = session.create({
                'name': 'Session',
                'start_balance': box.start_balance,
                'start_date': datetime.today(),
                'box': box.id,
                'journals': [(6, 0, box.journals.ids)]
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }

    @staticmethod
    def get_user_opened_session(box):
        session = box.env['treasury.box.session'].search([('create_uid', '=', box.env.uid), ('state', '=', 'opened')])
        return session

    @staticmethod
    def check_information(box):
        if box.state == 'closed':
            session = box.get_user_opened_session(box)
            if session:
                raise ValidationError(_('Can not open this box, please close your current session first '))

    @api.depends('journals')
    def _compute_start_balance(self):
        total = 0.0
        for res in self:
            for journal in res.journals:
                journal_data = res.get_current_balance(journal)
                total += journal_data['last_balance']
            res.start_balance = total
        return total

    @api.depends('journals')
    def _compute_end_balance(self):
        total = 0.0
        for res in self:
            for journal in self.journals:
                journal_data = res.get_current_balance(journal)
                total += journal_data['account_balance']
            res.end_balance = total
        return total

    @api.constrains('journals')
    def check_journals(self):
        if self.state == 'opened':
            raise ValidationError(_('You can not make box changes with sessions opened'))

        # for journal in self.journals:
        #     boxes = self.env['treasury.box'].search([])
        #     for box in boxes:
        #         if journal in box.journals:
        #             raise UserError(_("the journal %s is already associated with the box %s") % (journal.name,box.name))

    def unlink(self):
        for box in self:
            session = box.env['treasury.box.session'].search([])
            if session:
                raise ValidationError(_('You can not delete box with session'))
        return super(TreasuryBox, self).unlink()
