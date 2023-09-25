from odoo import fields, models, api


class TreasuryRequestApproval(models.Model):
    _name = 'treasury.request.approval'
    _description = 'Treasury Request Approvals'

    user_id = fields.Many2one(comodel_name="res.users", string="User")
    approve = fields.Boolean(string="Approve")
    treasury_request = fields.Many2one(comodel_name="treasury.request")
