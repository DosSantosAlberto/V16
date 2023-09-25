from odoo import fields, models, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    amount_total_wth = fields.Monetary(_('Total w/ Withhold'), store=True,
                                       currency_field='currency_id', compute='_amount_all')

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_wth = amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                line._compute_amount()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_wth += sum(line.price_subtotal * (tax.amount / 100) for tax in line.taxes_id if
                    tax.is_withholding)
            currency = order.currency_id or order.partner_id.property_purchase_currency_id or self.env.company.currency_id
            order.update({
                'amount_untaxed': currency.round(amount_untaxed),
                'amount_tax': currency.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'amount_total_wth': amount_untaxed + amount_tax - amount_wth if amount_wth else 0
            })

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        vals = super()._convert_to_tax_base_line_dict()
        taxes = self.taxes_id.filtered(lambda tax: not tax.is_withholding or not tax.invoice_not_affected)
        vals.update({"taxes": taxes})
        return vals
