from odoo import fields, models, api


class HtStockPicking(models.Model):
    _inherit = 'stock.picking'

    guide_sequence = fields.Char(string="Guide Sequence")
    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    has_cost_center = fields.Boolean(related='company_id.stock_cost_center')

    def do_print_picking(self):
        self.write({'printed': True})
        return self.env.ref('stock.action_report_delivery').report_action(self)

    def button_transport_slip(self):
        return self.env.ref('ht_stock_ao.action_report_transport_slip_ao').report_action(self)

    def button_validate(self):
        result = super(HtStockPicking, self).button_validate()
        sequence = self.env['ir.sequence'].next_by_code('stock.picking.ao') or '/'
        self.guide_sequence = sequence
        return result
