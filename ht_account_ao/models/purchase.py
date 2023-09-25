from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    has_cost_center = fields.Boolean(related='company_id.purchase_cost_center')
    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
