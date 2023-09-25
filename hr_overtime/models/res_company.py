from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    rate_overtime_normal = fields.Float(string="Rate Overtime Normal", min=10, max=50)
    rate_overtime_exceed = fields.Float(string="Rate Overtime Exceed", min=20, max=75)
    day_overtime = fields.Float(string="Day overtime", default=2)
    month_overtime = fields.Float(string="Month overtime", default=40)
    year_overtime = fields.Float(string="Year overtime", default=200)
