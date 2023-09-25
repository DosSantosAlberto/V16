from odoo import models, fields, _


class Company(models.Model):
    _inherit = 'res.company'

    logo_size = fields.Integer('Logo Size', size=400, default=80)
