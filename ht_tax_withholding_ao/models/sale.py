from odoo import fields, models, api
import logging
import json

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    amount_total_wth = fields.Monetary('Total w/ Withhold', store=True, readonly=True)

    @staticmethod
    def _get_withhold_tax_line(price_subtotal, tax_id):
        """return: data for all taxes - @author: Hermenegildo Mulonga """
        tax_lines_data = []
        for tax in tax_id:
            if tax.tax_exigibility == 'withholding':
                return price_subtotal * (tax.amount / 100)
        return 0

    def get_withholding_tax(self):
        """return:  amount total tax withholding - @author: Hermenegildo Mulonga """
        withholding_tax_amount = 0
        for line in self.get_tax_line_details():
            if line['tax_exigibility'] == 'withholding':
                withholding_tax_amount += line['tax_amount']
        return withholding_tax_amount

    def ks_calculate_discount(self):
        """ change the method of calculating discount  @author: Hermenegildo Mulonga / Halow Tecnology """
        for rec in self:
            if rec.company_id.ht_discount_to == 'after_tax':

                if rec.ks_global_discount_type == "amount":
                    if rec.ks_global_discount_rate > 0.0:
                        rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0

                elif rec.ks_global_discount_type == "percent":
                    if rec.ks_global_discount_rate != 0.0:
                        discount_amount = (rec.amount_untaxed + rec.amount_tax) * rec.ks_global_discount_rate / 100
                        rec.ks_amount_discount = discount_amount
                    else:
                        rec.ks_amount_discount = 0
                elif not rec.ks_global_discount_type:
                    rec.ks_amount_discount = 0
                    rec.ks_global_discount_rate = 0

                _wth_tax_amount = rec.get_withholding_tax()
                rec.amount_tax = rec.amount_tax - _wth_tax_amount
                _amount_total = rec.amount_untaxed + rec.amount_tax
                rec.amount_total = _amount_total - rec.ks_amount_discount
                if _wth_tax_amount:
                    rec.amount_total_wth = (_amount_total - _wth_tax_amount) - rec.ks_amount_discount
            else:
                """@author: Hermenegildo Mulonga / Halow Tecnology """
                if rec.ks_global_discount_type == "amount":
                    if rec.ks_global_discount_rate > 0:
                        rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0

                elif rec.ks_global_discount_type == "percent":
                    if rec.ks_global_discount_rate > 0:
                        price_subtotal = sum([
                            line.price_unit * (1 - (line.discount or 0.0) / 100.0) * line.product_uom_qty for line in
                            rec.order_line
                        ])
                        rec.ks_amount_discount = price_subtotal * (rec.ks_global_discount_rate / 100)

                # rec.amount_tax = rec.amount_tax - rec.get_withholding_tax()
                _wth_tax_amount = rec.get_withholding_tax()
                _amount_total = rec.amount_untaxed + rec.amount_tax
                rec.amount_total = rec.amount_untaxed + rec.amount_tax
                if _wth_tax_amount:
                    rec.amount_total_wth = (rec.amount_total - _wth_tax_amount)
