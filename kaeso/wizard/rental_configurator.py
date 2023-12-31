# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
import math
from datetime import date


class KaesoRentalWizard(models.TransientModel):
    _inherit = 'rental.wizard'

    use_order_pricelist = fields.Boolean('Use Price List from Order', default=True)

    @api.onchange('pricing_id', 'currency_id', 'duration', 'duration_unit', 'use_order_pricelist')
    def _compute_unit_price(self):
        for wizard in self:
            unit_price = price = 0
            if wizard.pricelist_id:
                if wizard.use_order_pricelist:
                    price = wizard.pricelist_id._get_product_price(wizard.product_id, wizard.quantity, None)
                    if wizard.pricing_id:
                        unit_price = wizard.pricing_id.with_context(price=price)._compute_price(wizard.duration,
                                                                                            wizard.duration_unit)
                    wizard.unit_price = unit_price
                else:
                    wizard.unit_price = wizard.pricelist_id._get_product_price(
                        wizard.product_id, 1, start_date=wizard.pickup_date,
                        end_date=wizard.return_date
                    )
            elif wizard.pricing_id and wizard.duration > 0:
                if wizard.use_order_pricelist:
                    price = wizard.pricelist_id._get_product_price(wizard.product_id, wizard.quantity, None)
                    unit_price = wizard.pricing_id.with_context(price=price)._compute_price(wizard.duration,
                                                                                            wizard.duration_unit)
                else:
                    unit_price = wizard.pricing_id._compute_price(wizard.duration, wizard.duration_unit)

                if wizard.currency_id != wizard.pricing_id.currency_id:
                    wizard.unit_price = wizard.pricing_id.currency_id._convert(
                        from_amount=unit_price,
                        to_currency=wizard.currency_id,
                        company=wizard.company_id,
                        date=fields.Date.today())
                else:
                    wizard.unit_price = unit_price
            elif wizard.duration > 0:
                wizard.unit_price = wizard.product_id.lst_price

            product_taxes = wizard.product_id.taxes_id.filtered(lambda tax: tax.company_id.id == wizard.company_id.id)
            if wizard.rental_order_line_id:
                product_taxes_after_fp = wizard.rental_order_line_id.tax_id
            elif 'sale_order_line_tax_ids' in self.env.context:
                product_taxes_after_fp = self.env['account.tax'].browse(
                    self.env.context['sale_order_line_tax_ids'] or [])
            else:
                product_taxes_after_fp = product_taxes

            # TODO : switch to _get_tax_included_unit_price() when it allow the usage of taxes_after_fpos instead
            # of fiscal position. We cannot currently use the fpos because JS only has access to the line information
            # when opening the wizard.
            product_unit_price = wizard.unit_price
            if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_before_fp):
                    taxes_res = flattened_taxes_before_fp.compute_all(
                        product_unit_price,
                        quantity=wizard.quantity,
                        currency=wizard.currency_id,
                        product=wizard.product_id,
                    )
                    product_unit_price = taxes_res['total_excluded']

                flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_unit_price,
                        quantity=wizard.quantity,
                        currency=wizard.currency_id,
                        product=wizard.product_id,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            product_unit_price += tax_res['amount']
                wizard.unit_price = product_unit_price

    @api.depends('unit_price', 'pricing_id')
    def _compute_pricing_explanation(self):
        translated_pricing_duration_unit = dict()
        for key, value in self.pricing_id.recurrence_id._fields['unit']._description_selection(self.env):
            translated_pricing_duration_unit[key] = value
        for wizard in self:
            if wizard.pricing_id and wizard.duration > 0 and wizard.unit_price != 0.0:
                if wizard.pricing_id.recurrence_id.duration > 0:
                    pricing_price = wizard.pricing_id.price
                    if wizard.use_order_pricelist:
                        pricing_price = wizard.pricelist_id._get_product_price(wizard.product_id, wizard.quantity, None)

                    pricing_explanation = "%i * %i %s (%s)" % (
                        math.ceil(wizard.duration / wizard.pricing_id.recurrence_id.duration),
                        wizard.pricing_id.recurrence_id.duration,
                        translated_pricing_duration_unit[wizard.pricing_id.recurrence_id.unit],
                        self.env['ir.qweb.field.monetary'].value_to_html(pricing_price, {
                            'from_currency': wizard.pricing_id.currency_id,
                            'display_currency': wizard.pricing_id.currency_id, 'company_id': self.env.company.id, }))
                else:
                    pricing_explanation = _("Fixed rental price")
                if wizard.product_id.extra_hourly or wizard.product_id.extra_daily:
                    pricing_explanation += "<br/>%s" % (_("Extras:"))
                if wizard.product_id.extra_hourly:
                    pricing_explanation += " %s%s" % (
                        self.env['ir.qweb.field.monetary'].value_to_html(wizard.product_id.extra_hourly, {
                            'from_currency': wizard.product_id.currency_id,
                            'display_currency': wizard.product_id.currency_id, 'company_id': self.env.company.id, }),
                        _("/hour"))
                if wizard.product_id.extra_daily:
                    pricing_explanation += " %s%s" % (
                        self.env['ir.qweb.field.monetary'].value_to_html(wizard.product_id.extra_daily, {
                            'from_currency': wizard.product_id.currency_id,
                            'display_currency': wizard.product_id.currency_id, 'company_id': self.env.company.id, }),
                        _("/day"))
                wizard.pricing_explanation = pricing_explanation

                wizard.product_id.sudo().write({'duration': wizard.duration, 'duration_unit': wizard.duration_unit})
            else:
                # if no pricing on product: explain only sales price is applied ?
                if not wizard.product_id.product_pricing_ids and wizard.duration:
                    wizard.pricing_explanation = _(
                        "No rental price is defined on the product.\nThe price used is the sales price.")
                else:
                    wizard.pricing_explanation = ""

                wizard.product_id.sudo().write({'duration': wizard.duration, 'duration_unit': wizard.duration_unit})
