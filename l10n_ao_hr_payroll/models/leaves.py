from odoo import fields, models, api


class HolidaysStatus(models.Model):
    _inherit = 'hr.leave'

    code = fields.Char('Code', size=6, help='Type here a code for this Leave Type')
