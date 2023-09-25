from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    reason_code = fields.Char(string='Reason Code', compute='_account_code', store=True)
    integrator_code = fields.Char(string="Integrator Code", compute='_account_code', store=True)
    account_code = fields.Char(string="Account Code", compute='_account_code', store=True)
    move_id_state = fields.Selection(related='move_id.state', string="state", store=True)

    @api.depends('account_id')
    def _account_code(self):
        for res in self:
            res.reason_code = res.account_id.reason_code
            res.integrator_code = res.account_id.integrator_code
            res.account_code = res.account_id.code
