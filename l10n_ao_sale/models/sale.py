from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from functools import partial
from datetime import datetime, date, timedelta
from odoo.tools.misc import formatLang
from odoo.tools import float_compare
from odoo.addons.l10n_ao_sale.sign import sign


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_total_wth = fields.Monetary(_('Total w/ Withhold'), store=True, currency_field='currency_id',
                                       compute='_compute_amounts')
    hash = fields.Char(string="Hash", copy=False, readonly=True)
    hash_control = fields.Char(string="Hash Control", default="0")
    hash_to_sign = fields.Char(string="Hash to sign")
    saft_status_date = fields.Datetime("SAFT Status Date")
    system_entry_date = fields.Datetime("Signature Datetime", copy=False)
    partner_name = fields.Char("Name")
    partner_street = fields.Char("Street")
    partner_street2 = fields.Char("Street2")
    partner_city = fields.Char("City")
    partner_state = fields.Char("State")
    partner_vat = fields.Char("NIF")
    document_type_id = fields.Many2one("sale.order.document.type", "Document Type")
    state = fields.Selection(selection_add=[("valid", "Valid"), ('sent',)], ondelete={"valid": "set default"})
    secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False)
    amount_discount = fields.Monetary(_('Total Discounts'), store=True, currency_field='currency_id',
                                      compute='_compute_amount_discount')
    company_country_id = fields.Many2one(related="company_id.country_id")

    def action_validate(self):
        for order in self:
            order.state = 'valid'
        return {}

    def action_cancel_new(self):
        return self.action_cancel()

    def action_quotation_send_new(self):
        return self.action_quotation_send()

    @api.depends('order_line.product_uom_qty', 'order_line.price_unit', 'order_line.discount')
    def _compute_amount_discount(self):
        for sale in self:
            total_price = 0
            discount_amount = 0
            for line in sale.order_line.filtered(lambda l: l.discount > 0):
                total_price = (line.product_uom_qty * line.price_unit) * (line.discount / 100)
                tax_include = line.tax_id.filtered(lambda tax: tax.price_include)
                if tax_include:
                    total_price = total_price / ((tax_include.amount + 100) / 100)
                discount_amount += total_price
            sale.update({'amount_discount': discount_amount})

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.company_id.country_id.code == "AO":
            if self.state == "valid":
                if self.env.context.get('mark_so_as_sent'):
                    self.filtered(lambda o: o.state == 'valid').with_context(tracking_disable=True).write(
                        {'state': 'sent'})
        else:
            if self.env.context.get('mark_so_as_sent'):
                self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        return super(SaleOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

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
        return True

    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        for order in self:
            # if float_compare(order.amount_total, 0.0, precision_rounding=order.currency_id.rounding) == -1:
            #      raise ValidationError(_('You cannot validate an sales order with a negative total amount!'))
            pass

    @api.constrains('partner_id')
    def set_customer_data(self):
        if self.state not in ['sale', 'sent']:
            dict_val = {"partner_name": self.partner_id.display_name, "partner_street": self.partner_id.street,
                        "partner_street2": self.partner_id.street2,
                        "partner_state": self.partner_id.state_id.name, "partner_city": self.partner_id.city,
                        "partner_vat": self.partner_id.vat}
            res = self.write(dict_val)
            return res

    def _amount_line_tax_ex(self, line):
        val = 0.0
        tax_obj = self.env['account.tax']
        for c in line.tax_id.compute_all(
                line.price_unit * (1 - (line.discount or 0.0) / 100.0), None,
                line.product_uom_qty, line.product_id, line.order_id.partner_id)[
            'taxes']:
            if tax_obj.browse(c['id']).tax_payment_type not in ['payment', 'withholding']:
                val += c.get('amount', 0.0)

        return val

    # Overwrite
    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            amount_wth = order.amount_untaxed = order.amount_tax = 0.0
            amount_untaxed_wth = 0
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.amount_untaxed = sum(order_lines.mapped('price_subtotal'))
            order.amount_total = sum(order_lines.mapped('price_total'))
            order.amount_tax = sum(order_lines.mapped('price_tax'))
            for line in order.order_line:
                amount_untaxed_wth += sum(line.price_subtotal for tax in order_lines.tax_id if tax.is_withholding)
                amount_wth += sum(line.price_subtotal * (tax.amount / 100) for tax in order_lines.tax_id if
                                  tax.is_withholding is True and line.price_subtotal > tax.threshold_wht)
            order.update(
                {'amount_total_wth': (amount_untaxed_wth - amount_wth) + order.amount_tax if amount_wth else 0})

    # # Overwrite
    # @api.depends('order_line.price_total')
    # def _amount_all(self):
    #     """
    #     Compute the total amounts of the SO.
    #     """
    #     for order in self:
    #         amount_wth = amount_untaxed = amount_tax = 0.0
    #         for line in order.order_line:
    #             amount_untaxed += line.price_subtotal
    #             amount_tax += line.price_tax
    #             amount_wth += sum(line.price_subtotal * (tax.amount / 100) for tax in line.tax_id if
    #                               tax.is_withholding)
    #         order.update({
    #             'amount_untaxed': amount_untaxed,
    #             'amount_tax': amount_tax,
    #             'amount_total': amount_untaxed + amount_tax,
    #             'amount_total_wth': amount_untaxed + amount_tax - amount_wth if amount_wth else 0
    #         })
    #         return

    def _amount_by_group(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.order_line:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id,
                                                partner=order.partner_shipping_id)['taxes']
                for tax in line.tax_id:
                    if tax.tax_exigibility == 'on_payment' and tax.is_withholding:
                        continue
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]

    def get_content_to_sign(self):
        res = ""
        if self.secure_sequence_number - 1 >= 1:
            last_orders = self.env['sale.order'].search(
                [('state', 'in', ['sent', 'sale', 'valid']),  # ('type_name', '=', 'Sale Order'),
                 ('id', "!=", self.id), ("date_order", "<=", self.date_order),
                 # ("confirmation_date", "<=", sale.confirmation_date),
                 ('system_entry_date', '<=', self.system_entry_date),
                 ("document_type_id", "<=", self.document_type_id.id),
                 ('company_id', '=', self.company_id.id),
                 ('secure_sequence_number', '=', self.secure_sequence_number - 1), ],
                order="system_entry_date desc", limit=1)
            if last_orders and last_orders.hash:
                last_order_hash = last_orders.hash
                system_entry_date = self.system_entry_date.isoformat(sep='T',
                                                                     timespec='auto') if self.system_entry_date else fields.Datetime.now().isoformat(
                    sep='T', timespec='auto')
                res = ";".join((fields.Date.to_string(self.date_order), system_entry_date,
                                self.name, str(format(self.amount_total, '.2f')),
                                last_order_hash))

        elif self.secure_sequence_number - 1 == 0:
            system_entry_date = self.system_entry_date.isoformat(sep='T',
                                                                 timespec='auto') if self.system_entry_date else fields.Datetime.now().isoformat(
                sep='T', timespec='auto')
            res = ";".join((fields.Date.to_string(self.date_order), system_entry_date, self.name,
                            str(format(self.amount_total, '.2f')), ""))
        return res

    def sign_document(self, content_data):
        response = ''
        if content_data:
            response = sign.sign_content(content_data)
        if response:
            return response
        return content_data

    def resign(self, order):
        content_hash = order.get_content_to_sign()[0]
        hash_to_sign = content_hash
        content_signed = order.sign_document(content_hash).split(";")
        if content_hash != content_signed:
            hash_control = content_signed[1] if len(content_signed) >= 1 else "0"
            hash = content_signed[0]
        orders = {
            "hash_control": hash_control,
            "hash": hash,
            "hash_to_sign": hash_to_sign
        }
        order.write(orders)

    @api.model
    def resign_content(self, from_date):
        orders = self.env['sale.order'].search(
            [("state", "in", ["sale"]),
             ("date_order", ">=", from_date)],
            order="system_entry_date asc,date_order asc")
        if orders:
            orders.write({"hash": "", "hash_control": "", "hash_to_sign": ""})
            [order.write({"hash": "", "hash_control": "", "hash_to_sign": ""}) for order in orders]
            for order in orders:
                order.resign(order)

    def _check_data_order(self):
        if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_date'):
            if self.validity_date and self.type_name == "Quotation" and self.company_id.country_id.code == "AO" \
                    and self.state == 'draft':
                orders = self.env['sale.order'].search(
                    [('state', 'in', ['sent', 'sale']), '|',
                     ('date_order', '!=', None),  # ('confirmation_date', '!=', None)
                     ('company_id', '=', self.company_id.id)],
                    order="validity_date desc", limit=1
                )
                last_date_order = orders.filtered(lambda r: r.date_order > self.date_order)
                if last_date_order:
                    raise ValidationError(_("Can not create orders, whose date is before date %s") % (
                        fields.Date.to_string(last_date_order[0].date_order)))

    def _check_system_datetime(self):
        if self.company_id.country_id.code == "AO" and self.state in ['draft', 'sent']:
            orders = self.env['sale.order'].search(
                [('state', 'in', ['sent', 'sale']),  # ('type_name', '=', 'Sale Order'),
                 ('system_entry_date', '!=', None),
                 ('company_id', '=', self.company_id.id)],
                order="system_entry_date desc", limit=1
            )
            last_system_entry_date = orders.filtered(lambda r: r.system_entry_date > fields.Datetime.now())
            if last_system_entry_date:
                raise ValidationError(_(
                    "There is a mismatch of the time of your computer and the last order created.\n Check if you system date it's correct!"))

    @api.constrains('state')
    def _check_document_type_product(self):
        for sale in self:
            if self.company_id.country_id.code == "AO":
                if sale.state == 'valid':
                    product_types = sale.order_line.mapped('product_id').mapped('type')
                    if product_types:
                        if self.document_type_id.code == 'PP':
                            if any(elem == 'consu' or elem == 'product' for elem in product_types):
                                a = 1
                            else:
                                raise ValidationError(_(
                                    "The %s document type does not allow the sale of only items of type service.") % self.document_type_id.name)

                        if self.document_type_id.code == 'OR':
                            if 'service' in product_types:
                                a = 1
                            else:
                                raise ValidationError(_(
                                    "The %s document type does not allow the sale of only items of type product.") % self.document_type_id.name)

    # @api.model
    # def create(self, vals):
    #     if self.company_id.country_id.code == "AO":
    #         vals['system_entry_date'] = fields.Datetime.now()
    #         vals['saft_status_date'] = fields.Datetime.now()
    #
    #         ret = super(SaleOrder, self).create(vals)
    #         content_hash = ret.get_content_to_sign()
    #         ret.hash_to_sign = content_hash
    #         content_signed = ret.sign_document(content_hash).split(";")
    #         if content_hash != content_signed:
    #             ret.hash_control = content_signed[1] if len(content_signed) > 1 else "0"
    #             ret.hash = content_signed[0]
    #
    #         return ret
    #
    #     else:
    #         return super(SaleOrder, self).create(vals)

    def write(self, values):
        res = []
        if self.company_id.country_id.code == "AO":
            # self._check_document_type_product(values)
            for order in self:
                if order.state == 'draft' and order.system_entry_date == False:
                    if 'OU' in order.name:
                        pass
                    else:
                        values['name'] = "draft"
                    if not self.document_type_id:
                        values['document_type_id'] = self.env.user.company_id.document_type_id.id

                order._check_system_datetime()
                if values.get('state') in ["sale", "sent", "valid"] and order.state in ['draft']:
                    order._check_data_order()
                    if order.system_entry_date == False:
                        if order.name == 'draft' and order.state == 'draft':
                            if self.document_type_id.code == 'OU':
                                sequence = self.env['ir.sequence'].with_company(self.company_id).search(
                                    []).next_by_code(
                                    'OU')
                                secure_sequence_number = sequence.split("/")[1]
                                values['name'] = f'{self.document_type_id.code} {sequence}'
                                values['secure_sequence_number'] = secure_sequence_number
                            elif self.document_type_id.code == 'OR':
                                sequence = self.env['ir.sequence'].with_company(self.company_id).search(
                                    []).next_by_code(
                                    'OR')
                                secure_sequence_number = sequence.split("/")[1]
                                values['name'] = f'{self.document_type_id.code} {sequence}'
                                values['secure_sequence_number'] = secure_sequence_number
                            elif self.document_type_id.code == 'PP':
                                sequence = self.env['ir.sequence'].with_company(self.company_id).search(
                                    []).next_by_code(
                                    'PP')
                                secure_sequence_number = sequence.split("/")[1]
                                values['name'] = f'{self.document_type_id.code} {sequence}'
                                values['secure_sequence_number'] = secure_sequence_number

                        values['system_entry_date'] = fields.Datetime.now()
                    values['saft_status_date'] = fields.Datetime.now()

                    if not order.order_line:
                        raise UserError(
                            _("Deve adicionar um (produto/serviço) a linha, para que possa prosseguir com a validação do documento."))

                    if not order.hash:
                        if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_tax'):
                            for line in order.order_line.filtered(
                                    lambda r: r.display_type not in ['line_note', 'line_section']):
                                lines_tax = line.tax_id.filtered(
                                    lambda t: (t.saft_tax_code == 'NOR' and t.saft_tax_type in ['IVA']) or
                                              (t.saft_tax_code in ['NS', 'ISE'] and t.saft_tax_type in ['NS', 'IVA']))

                                if not lines_tax and values.get('state') not in ["draft"]:
                                    raise UserError(
                                        _(
                                            "There are missing taxes in the order line!\n If this is a duty-free product, please add"
                                            " the tax that corresponds to the specific duty-free tax. If not, it will not be "
                                            "possible to validate your SAFT file upon submission!"))

                        res = super(SaleOrder, self).write(values)
                        content_hash = order.get_content_to_sign()
                        values['hash_to_sign'] = content_hash
                        content_signed = order.sign_document(content_hash).split(";")
                        if content_hash != content_signed:
                            values['hash_control'] = content_signed[1] if len(content_signed) > 1 else "0"
                            values['hash'] = content_signed[0]
        res = super(SaleOrder, self).write(values)
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.constrains('discount')
    def _check_discount(self):
        for order in self:
            if self.company_id.country_id.code == "AO" and (order.discount < 0 or order.discount > 100):
                raise ValidationError(_("the discount must be between 0 and 100 %."))

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_recordset(['invoice_repartition_line_ids'])

    @api.constrains('product_id')
    def _check_product(self):

        if self.company_id.country_id.code == "AO":
            for line in self.filtered(
                    lambda r: r.display_type not in ['line_note', 'line_section']):
                lines_tax = line.tax_id.filtered(
                    lambda t: (t.saft_tax_code == 'NOR' and t.saft_tax_type in ['IVA']) or
                              (t.saft_tax_code in ['NS', 'ISE'] and t.saft_tax_type in ['NS', 'IVA']))

                if not lines_tax:
                    raise UserError(
                        _(
                            "There are missing taxes in the order line!\n If this is a duty-free product, please add"
                            " the tax that corresponds to the specific duty-free tax. If not, it will not be "
                            "possible to validate your SAFT file upon submission!"))
