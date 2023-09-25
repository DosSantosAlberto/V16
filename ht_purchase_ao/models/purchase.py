from odoo import fields, models, api


class HtPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    has_cost_center = fields.Boolean(related='company_id.purchase_cost_center')

    def _prepare_invoice(self):
        values = super(HtPurchaseOrder, self)._prepare_invoice()
        values['cost_center'] = self.cost_center.id
        return values

    def _prepare_picking(self):
        values = super(HtPurchaseOrder, self)._prepare_picking()
        values['cost_center'] = self.cost_center.id
        return values
