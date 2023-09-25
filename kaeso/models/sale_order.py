from odoo import models, fields, api, _
from odoo.tools.misc import formatLang, get_lang
from datetime import timedelta, date
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'sale.order'

    # forecast = fields.Boolean(string="Forecast")
    # proforma_waiting_for_e_s_j_p_c_p_o = fields.Boolean(string="Proforma waiting for E.S / J.P.C / P.O")
    # proforma_waiting_for_validation = fields.Boolean(string="Proforma waiting for validation")
    # rental_status = fields.Selection(selection_add=[("valid", "Valid"), ('sent',)])
    # date_order = fields.Datetime(string='Order Date', required=True, readonly=False, index=True,
    #                              states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False,
    #                              default=fields.Datetime.now,
    #                              help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.")

    po_file_attachment = fields.Many2one("ir.attachment")
    team_id = fields.Many2one('crm.team', string='Sales Team', check_company=True, index=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", ondelete="set null",
                              readonly=False)

    def action_validate(self):
        for order in self:
            order.document_type_id = self.env.user.company_id.document_type_id.id
        return super(AccountInvoice, self).action_validate()


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    duration = fields.Integer(related="product_id.duration")
    duration_unit = fields.Selection(related="product_id.duration_unit")

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(lang=get_lang(self.env, self.order_id.partner_id.lang).code,
                                               partner=self.order_id.partner_id,
                                               quantity=vals.get('product_uom_qty') or self.product_uom_qty,
                                               date=self.order_id.date_order, pricelist=self.order_id.pricelist_id.id,
                                               uom=self.product_uom.id)

        vals.update(name=self._get_sale_order_line_multiline_description_sale())

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = product._get_tax_included_unit_price(self.company_id, self.order_id.currency_id,
                                                                      self.order_id.date_order, 'sale',
                                                                      fiscal_position=self.order_id.fiscal_position_id,
                                                                      product_price_unit=self._get_display_price(),
                                                                      product_currency=self.order_id.currency_id)
        if self.is_rental:
            vals['duration'] = self.product_id.duration
            vals['duration_unit'] = self.product_id.duration_unit

        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s", product.name)
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False

        return result

    # def _move_serials(self, lot_ids, location_id, location_dest_id):
    #     """Move the given lots from location_id to location_dest_id.
    #
    #     :param stock.production.lot lot_ids:
    #     :param stock.location location_id:
    #     :param stock.location location_dest_id:
    #     """
    #     if not lot_ids:
    #         return
    #
    #     location_dest_id = self.order_id.partner_id.property_stock_customer
    #
    #     rental_stock_move = self.env['stock.move'].create({
    #         'product_id': self.product_id.id,
    #         'product_uom_qty': len(lot_ids),
    #         'product_uom': self.product_id.uom_id.id,
    #         'location_id': location_id.id,
    #         'location_dest_id': location_dest_id.id,
    #         'partner_id': self.order_partner_id.id,
    #         'sale_line_id': self.id,
    #         'name': _("Rental move :") + " %s" % (self.order_id.name),
    #     })
    #
    #     for lot_id in lot_ids:
    #         lot_quant = self.env['stock.quant']._gather(self.product_id, location_id, lot_id)
    #         lot_quant = lot_quant.filtered(lambda quant: quant.quantity == 1.0)
    #         if not lot_quant:
    #             raise ValidationError(_("No valid quant has been found in location %s for serial number %s !") % (
    #             location_id.name, lot_id.name))
    #             # Best fallback strategy??
    #             # Make a stock move without specifying quants and lots?
    #             # Let the move be created with the erroneous quant???
    #         # As we are using serial numbers, only one quant is expected
    #         ml = self.env['stock.move.line'].create(rental_stock_move._prepare_move_line_vals(reserved_quant=lot_quant))
    #         ml['qty_done'] = 1
    #
    #     rental_stock_move._action_done()
    #
    # def _return_serials(self, lot_ids, location_id, location_dest_id):
    #     """Undo the move of lot_ids from location_id to location_dest_id.
    #
    #     :param stock.production.lot lot_ids:
    #     :param stock.location location_id:
    #     :param stock.location location_dest_id:
    #     """
    #     # VFE NOTE : or use stock moves to undo return/pickups ???
    #     if not lot_ids:
    #         return
    #
    #     location_id = self.order_id.partner_id.property_stock_customer
    #
    #     rental_stock_move = self.env['stock.move'].search([
    #         ('sale_line_id', '=', self.id),
    #         ('location_id', '=', location_id.id),
    #         ('location_dest_id', '=', location_dest_id.id)
    #     ])
    #     for ml in rental_stock_move.mapped('move_line_ids'):
    #         # update move lines qties.
    #         if ml.lot_id.id in lot_ids:
    #             ml.qty_done = 0.0
    #
    #     rental_stock_move.product_uom_qty -= len(lot_ids)
    #
    # def _move_qty(self, qty, location_id, location_dest_id):
    #     """Move qty from location_id to location_dest_id.
    #
    #     :param float qty:
    #     :param stock.location location_id:
    #     :param stock.location location_dest_id:
    #     """
    #     if location_dest_id == self.company_id.rental_loc_id:
    #         location_dest_id = self.order_id.partner_id.property_stock_customer
    #
    #     if location_id == self.company_id.rental_loc_id:
    #         location_id = self.order_id.partner_id.property_stock_customer
    #
    #     rental_stock_move = self.env['stock.move'].create({
    #         'product_id': self.product_id.id,
    #         'product_uom_qty': qty,
    #         'product_uom': self.product_id.uom_id.id,
    #         'location_id': location_id.id,
    #         'location_dest_id': location_dest_id.id,
    #         'partner_id': self.order_partner_id.id,
    #         'sale_line_id': self.id,
    #         'name': _("Rental move :") + " %s" % (self.order_id.name),
    #         'state': 'confirmed',
    #     })
    #     rental_stock_move._action_assign()
    #     rental_stock_move._set_quantity_done(qty)
    #     rental_stock_move._action_done()
    #
    # def _return_qty(self, qty, location_id, location_dest_id):
    #     """Undo a qty move (partially or totally depending on qty).
    #
    #     :param float qty:
    #     :param stock.location location_id:
    #     :param stock.location location_dest_id:
    #     """
    #
    #     location_dest_id = self.order_id.partner_id.property_stock_customer
    #
    #     # VFE NOTE : or use stock moves to undo return/pickups ???
    #     rental_stock_move = self.env['stock.move'].search([
    #         ('sale_line_id', '=', self.id),
    #         ('location_id', '=', location_id.id),
    #         ('location_dest_id', '=', location_dest_id.id)
    #     ], order='date desc')
    #
    #     for ml in rental_stock_move.mapped('move_line_ids'):
    #         # update move lines qties.
    #         qty -= ml.qty_done
    #         ml.qty_done = 0.0 if qty > 0.0 else -qty
    #
    #         if qty <= 0.0:
    #             return True
    #             # TODO ? ml.move_id.product_uom_qty -= decrease of qty
    #
    #     return qty <= 0.0


class KaesoProductProduct(models.Model):
    _inherit = 'product.product'

    duration = fields.Integer(string="Duration",
                              help="The duration unit is based on the unit of the rental pricing rule.")
    duration_unit = fields.Selection([("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months")])
