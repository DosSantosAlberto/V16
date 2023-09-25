from odoo import fields, models, api


class HtStockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
       values = super(HtStockMove, self)._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
       values['cost_center'] = self.picking_id.cost_center.id
       return values
