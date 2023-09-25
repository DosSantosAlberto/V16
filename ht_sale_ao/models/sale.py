from odoo import fields, models, api,_
from odoo.exceptions import ValidationError, UserError
import logging
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Angola Sale"

    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    has_cost_center = fields.Boolean(related='company_id.sale_cost_center')

    def _prepare_invoice(self):
        result = super(SaleOrder, self)._prepare_invoice()
        result['invoice_origin'] = self.name + ' - ' + fields.Datetime.to_string(self.date_order)[:10]
        result['cost_center'] = self.cost_center.id
        return result

    def action_confirm(self):
        if self.state == 'draft' and self.company_id.country_id.code == "AO":
            raise UserError(_(
                'It is not allowed to confirm an order in %s status, the document must be validated first'
            ) % self.state)

        if self.state == 'valid' or self.state == 'sent' and self.company_id.country_id.code == "AO":
            if self._get_forbidden_state_confirm() & set(self.mapped('state')):
                raise UserError(_(
                    'It is not allowed to confirm an order in the following states: %s'
                ) % (', '.join(self._get_forbidden_state_confirm())))
        elif self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)
        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        result = super(SaleOrder, self).action_confirm()
        for picking in self.picking_ids:
            if self.cost_center:
                picking.cost_center = self.cost_center.id
        return result

    def get_tax_line_details(self):
        """return: data for all taxes - @author: Hermenegildo Mulonga """
        tax_lines_data = []
        for line in self.order_line:
            for tax_line in line.tax_id:
                tax_lines_data.append({
                    'tax_exigibility': tax_line.tax_exigibility,
                    'tax_amount': line.price_subtotal * (tax_line.amount / 100),
                    'base_amount': line.price_subtotal,
                    'tax': tax_line,
                })
        return tax_lines_data

    def tax_of_invoice(self):
        taxes = []
        for line in self.order_line:
            for tax in line.tax_id:
                taxes.append(tax)
        return list(set(taxes))

    def amount_format(self, amount):
        return formatLang(self.env, amount)

