from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, Warning
from odoo.tools.misc import formatLang


class TreasuryCashFlowReport(models.TransientModel):
    _name = 'treasury.cash.flow.report'
    _description = 'Cash FLow Report'
    _rec_name = "start_date"

    start_date = fields.Datetime(string='Start Date', default=fields.datetime.now())
    end_date = fields.Datetime(string='End Date', default=fields.datetime.now())
    box_id = fields.Many2one(comodel_name='treasury.box', string='Box')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    @api.constrains('box_id', 'start_date')
    def check_box_session(self):
        session = self.env['treasury.box.session'].search([('box', '=', self.box_id.id), ('state', '=', 'opened')])
        if session:
            if session.start_date >= self.start_date:
                raise ValidationError(_('Please close the box first for view cash flow report'))

    def get_domain(self):
        domain = [('box', '=', self.box_id.id), ('start_date', '>=', self.start_date),
                  ('end_date', '<=', self.end_date)]
        return domain

    def get_sessions(self):
        domain = self.get_domain()
        sessions = self.env['treasury.box.session'].search(domain, order='start_date asc')
        return sessions

    def get_box_cash_flow(self):
        movement_list = []
        for session in self.get_sessions():
            for movement in session.session_lines:
                movement_list.append(movement)
        return movement_list

    def get_start_balance(self):
        result = self.get_sessions()
        if result:
            return result[0].start_balance
        return 0.0

    def get_end_balance(self):
        result = self.get_sessions()
        if result:
            return result[-1].end_balance
        return 0.0

    def print_report(self):
        if self.get_box_cash_flow():
            return self.env.ref('es_treasury.report_cash_flow').report_action(self)
        raise ValidationError(_('No records found for this date range!'))
