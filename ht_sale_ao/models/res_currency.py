from odoo import models, fields, _


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    amount_tax = fields.Float('Amount Tax', default=0)

