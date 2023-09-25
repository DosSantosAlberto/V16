from odoo import fields, models, api
from datetime import datetime, date, time


class TreasuryBoxClose(models.Model):
    _name = 'treasury.box.close'
    _description = 'name'

    name = fields.Char('Reference')
    start_balance = fields.Float(string='Starting Balance', compute='compute_start_balance', store=True)
    end_balance = fields.Float(string='Ending Balance')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal')
    state = fields.Selection([('new', 'New'), ('closed', 'Closed')], default='new')
    line_ids = fields.One2many('account.bank.statement.line', 'statement_id', string='Statement lines',
                               states={'closed': [('readonly', True)]}, copy=True)

    def close_box(self):
        pass

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self.get_opening_balance(self.journal_id)

    def get_opening_balance(self, journal):
        for res in self:
            result = res.env['account.bank.statement'].search([('journal_id', '=', journal.id), ('date', '<=', res.date)], order="date desc, id desc", limit=1)
            res.start_balance = result and result[0].balance_end or 0
            return res.start_balance

    @api.depends('journal_id')
    def compute_start_balance(self):
        self.get_opening_balance(self.journal_id)