from odoo import fields, models, api, _
from datetime import datetime, date


class BoxMovementWizard(models.TransientModel):
    _name = 'hs_tresury.box.movement'

    @api.model
    def get_default_user(self):
        if not self.all_users:
            self.users |= self.env.user

    start_date = fields.Datetime(string='Start Date', default=datetime.now())
    end_date = fields.Datetime(string='End Date', default=datetime.now())
    box = fields.Many2one(comodel_name='treasury.box', string='Box')
    users = fields.Many2many(comodel_name='res.users', string='User')
    all_users = fields.Boolean('Todos Utilizadores')

    def print_report(self):
        return self.env.ref('hs_treasury.report_box_movement').report_action(self)

    @api.onchange('all_users')
    def get_default_user(self):
        if not self.all_users:
            self.users |= self.env.user

    def get_domain(self):
        domain = [('box', '=', self.box.id), ('start_date', '>=', self.start_date),
                  ('end_date', '<=', self.end_date)]
        if not self.all_users:
            domain.append(('create_uid', 'in', self.users.ids))
        return domain

    def get_sessions(self):
        domain = self.get_domain()
        sessions = self.env['treasury.box.session'].search(domain, order='start_date asc')
        return sessions

    def get_session_by_date_and_box(self):
        movement_list = []
        for session in self.get_sessions():
            for movement in session.session_lines:
                movement_list.append(movement)
        return movement_list

    def get_start_balance(self):
        result = self.get_sessions()
        if result:
            return result[0].start_balance

    def get_end_balance(self):
        result = self.get_sessions()
        if result:
            return result[-1].end_balance
