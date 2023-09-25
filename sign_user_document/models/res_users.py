from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    signature_ids = fields.Many2many("signature.image", string="Signature Employ")
