# -*- coding: utf-8 -*-
from functools import partial
from odoo import models, fields, api, _
from contextlib import ExitStack, contextmanager
from odoo.tools.misc import formatLang
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero, float_compare, date_utils, DEFAULT_SERVER_DATE_FORMAT
from collections import defaultdict
from .saft import dict_clean_up
from odoo.addons.l10n_ao.sign import sign
from datetime import date, timedelta


class AccountInvoiceAO(models.Model):
    _inherit = "account.move"

    _order = "invoice_date desc, system_entry_date desc, name desc, id desc"

    partner_name = fields.Char("Name", compute='set_customer_data', store=True)
    partner_street = fields.Char("Street", compute='set_customer_data', store=True)
    partner_street2 = fields.Char("Street2", compute='set_customer_data', store=True)
    partner_city = fields.Char("City", compute='set_customer_data', store=True)
    partner_state = fields.Char("State", compute='set_customer_data', store=True)
    partner_vat = fields.Char("NIF", compute='set_customer_data', store=True)
    hash = fields.Char(string="Hash", copy=False, readonly=True)
    hash_control = fields.Char(string="Hash Control", copy=False, default="0")
    hash_to_sign = fields.Char(string="Has to sign")
    saft_status_date = fields.Datetime("SAFT Status Date", copy=False)
    system_entry_date = fields.Datetime("Signature Datetime", copy=False)
    payment_has_withholded = fields.Boolean(_('Invoice was withholded'))
    amount_total_wth = fields.Monetary(_('Total w/ Withhold'), store=True,
                                       currency_field='currency_id', compute='_compute_amount')
    regime = fields.Char("Regime", compute='set_customer_data', store=True)
    amount_discount = fields.Monetary(_('Total Discounts'), store=True,
                                      currency_field='currency_id', compute='_compute_amount_discount')
    total_invoiced = fields.Integer(_('total invoiced'), compute='compute_total_invoiced')
    counter_currency_id = fields.Many2one('res.currency', string='Counter currency')
    counter_value = fields.Float(compute='_compute_counter_value', string='Counter value')
    exchange_rate = fields.Float(compute='_compute_counter_value', string='Exchange Rate')
    transaction_type = fields.Selection(string="Tipo de Lançamento",
                                        required=True,
                                        selection=[('N', 'Normal'),
                                                   ('R', 'Regularizações'),
                                                   ('A', 'Apur. Resultados'),
                                                   ('J', 'Ajustamentos')],
                                        help="Categorias para classificar os movimentos contabilísticos ao exportar o SAFT",
                                        default="N", )
    print_counter = fields.Integer("Control Number of printing", default=0, copy=False)
    company_code = fields.Char("Company Code", default=lambda self: self.env.user.company_id.country_id.code)

    def set_customer_data(self):
        for pt in self:
            if pt.state == "draft":
                pt.partner_name = pt.partner_id.display_name
                pt.partner_street = pt.partner_id.street
                pt.partner_street2 = pt.partner_id.street2
                pt.partner_state = pt.partner_id.state_id.name
                pt.partner_city = pt.partner_id.city
                pt.partner_vat = pt.partner_id.vat
                pt.regime = pt.company_id.tax_regime_id.name

    @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.price_unit', 'invoice_line_ids.discount')
    def _compute_amount_discount(self):
        for invoice in self:
            total_price = 0
            discount_amount = 0
            for line in invoice.invoice_line_ids.filtered(lambda l: l.discount > 0):
                total_price = (line.quantity * line.price_unit) * (line.discount / 100)
                tax_include = line.tax_ids.filtered(lambda tax: tax.price_include)
                if tax_include:
                    total_price = total_price / ((tax_include.amount + 100) / 100)
                discount_amount += total_price
            invoice.update({'amount_discount': discount_amount})

    def _compute_counter_value(self):
        if self.counter_currency_id:
            rate = self.env['res.currency']._get_conversion_rate(self.currency_id, self.counter_currency_id,
                                                                 self.company_id,
                                                                 self.invoice_date or fields.Date.today())
        else:
            rate = 0.0
        self.counter_value = self.amount_total * rate
        self.exchange_rate = 1 / (rate or 1)

    def _get_starting_sequence(self):
        self.ensure_one()
        if self.journal_id.type in ('sale', 'purchase') and self.company_id.country_id.code == "AO":
            if not self.journal_id.document_type:
                raise UserError(_("""You can't create an invoice without defining the document type in the sales 
                or purchase journal. Go to Configuration > Journal e define the document type"""))
            if self.journal_id.type == 'sale':
                if self.journal_id.document_type == self.journal_id.code:
                    starting_sequence = "%s %04d/0" % (self.journal_id.code, self.date.year)
                else:
                    starting_sequence = "%s %s%04d/0" % (
                    self.journal_id.document_type, self.journal_id.code, self.date.year)
                if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
                    if self.move_type == 'out_refund':
                        starting_sequence = starting_sequence.replace(self.journal_id.document_type, "NC")
                    if self.move_type == 'in_refund':
                        starting_sequence = starting_sequence.replace(self.journal_id.document_type, "ND")
            elif self.journal_id.type == 'purchase':
                if self.journal_id.code == "FTF":
                    starting_sequence = "%s %04d/0" % (self.journal_id.code, self.date.year)
                else:
                    starting_sequence = "%s %s%04d/0" % ("FTF", self.journal_id.code, self.date.year)
                if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
                    if self.move_type == 'out_refund':
                        starting_sequence = starting_sequence.replace("FTF", "NC")
                    if self.move_type == 'in_refund':
                        starting_sequence = starting_sequence.replace("FTF", "ND")
        else:
            starting_sequence = "%s/%04d/%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)
            if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
                starting_sequence = "R" + starting_sequence
        return starting_sequence

    @api.onchange('amount_total')
    def onchange_amount_total(self):
        if self.counter_currency_id:
            rate = self.env['res.currency']._get_conversion_rate(self.currency_id, self.counter_currency_id,
                                                                 self.company_id,
                                                                 self.invoice_date or fields.Date.today())
        else:
            rate = 0.0
        self.counter_value = self.amount_total * rate
        self.exchange_rate = 1 / (rate or 1)

    def get_content_to_sign(self):
        res = ""
        if self.sequence_number - 1 >= 1:
            last_invoices = self.env['account.move'].search(
                [('state', 'in', ['posted']), ('move_type', '=', self.move_type),
                 ('id', "!=", self.id), ('journal_id', '=', self.journal_id.id),
                 ('company_id', '=', self.company_id.id), ('sequence_number', '=', self.sequence_number - 1),
                 ('system_entry_date', '<=', self.system_entry_date)],
                order="system_entry_date desc", limit=1)
            if last_invoices:
                last_invoice_hash = last_invoices.hash if last_invoices.hash else ""
                system_entry_date = self.system_entry_date.isoformat(sep='T',
                                                                     timespec='auto') if self.system_entry_date else fields.Datetime.now().isoformat(
                    sep='T', timespec='auto')
                res = ";".join((fields.Date.to_string(self.invoice_date), system_entry_date,
                                self.name, str(format(self.amount_total, '.2f')),
                                last_invoice_hash))
        elif self.sequence_number - 1 == 0:
            system_entry_date = self.system_entry_date.isoformat(sep='T',
                                                                 timespec='auto') if self.system_entry_date else fields.Datetime.now().isoformat(
                sep='T', timespec='auto')
            res = ";".join((fields.Date.to_string(self.invoice_date), system_entry_date,
                            self.name, str(format(self.amount_total, '.2f')), ""))
        return res

    def sign_document(self, content_data):
        response = sign.sign_content(content_data)
        if response:
            return response
        return content_data

    def resign(self, inv):
        content_hash = inv.get_content_to_sign()
        hash_to_sign = content_hash
        content_signed = inv.sign_document(content_hash).split(";")
        if content_hash != content_signed:
            hash_control = content_signed[1] if len(content_signed) >= 1 else "0"
            hash = content_signed[0]
        invoices = {
            "hash_control": hash_control,
            "hash": hash,
            "hash_to_sign": hash_to_sign
        }
        inv.write(invoices)

    # override
    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        self = self.with_company(self.company_id)
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_company(self.journal_id.company_id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=',
                     'receivable' if self.move_type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date,
                                                                  currency=self.company_id.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date,
                                                                               currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                        'account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate.update(candidate._get_fields_onchange_balance(force_computation=True))
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id

        # AG Change to manage when we have a more that one receivable/payable account to the move line for the case
        # of captive vat.
        receivable_payable_line = self.env['account.move.line']
        if len(existing_terms_lines) > 1:
            if self.move_type == 'out_invoice':
                receivable_payable_line = existing_terms_lines.filtered(lambda l: l.balance < 0)
                # AG: This will verify if the account for receivable_payable_line line is different that the customer
                # account, if so is the case it will set the account for the customer account
                if receivable_payable_line and self.partner_id and \
                        receivable_payable_line.account_id != self.partner_id.property_account_receivable_id:
                    receivable_payable_line.account_id = self.partner_id.property_account_receivable_id
            if self.move_type == 'in_invoice':
                receivable_payable_line = existing_terms_lines.filtered(lambda l: l.balance > 0)
                # AG: This will verify if the account for receivable_payable_line line is different that the supplier
                # account, if so is the case it will set the account for the supplier account
                if receivable_payable_line and self.partner_id and \
                        receivable_payable_line.account_id != self.partner_id.property_account_payable_id:
                    receivable_payable_line.account_id = self.partner_id.property_account_payable_id
            others_lines += receivable_payable_line
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        if not receivable_payable_line:
            self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.payment_reference = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity

    def show_withholding(self):
        tax_lines = self.invoice_line_ids.mapped("tax_ids").filtered(lambda t: t.is_withholding)
        return tax_lines

    def get_taxes_by_group(self):
        for move in self:
            lang_env = move.with_context(lang=move.partner_id.lang).env
            invoice_tax_lines = move.invoice_line_ids.filtered(lambda line: line.tax_ids)
            tax_balance_multiplicator = -1 if move.is_inbound(True) else 1
            tax_include_amount = 0
            res = {}
            # There are as many tax line as there are repartition lines
            done_taxes = set()
            for line in invoice_tax_lines:
                for tax_id in line.tax_ids:
                    res.setdefault(tax_id, {'base': 0.0, 'amount': 0.0})
                    tax_amount = tax_id._compute_amount(
                        line.quantity * line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                        line.price_unit, line.quantity)
                    res[tax_id]['amount'] += tax_amount
                    tax_key_add_base = tuple([tax_id.id])
                    # if tax_key_add_base not in done_taxes:
                    # if line.currency_id and line.company_currency_id and line.currency_id != line.company_currency_id:
                    #     amount = line.company_currency_id._convert(line.quantity * line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                    #                                                line.currency_id,
                    #                                                line.company_id,
                    #                                                line.date or fields.Date.context_today(self))
                    # else:
                    amount = line.quantity * line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    res[tax_id]['base'] += amount
                    if tax_id.price_include:
                        res[tax_id]['base'] -= tax_amount
                    # The base should be added ONCE
                    done_taxes.add(tax_key_add_base)

            res = sorted(res.items(), key=lambda l: l[0].sequence)
            result = [(
                tax.name, amounts['amount'],
                amounts['base'],
                formatLang(lang_env, amounts['amount'], currency_obj=move.currency_id),
                formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                len(res),
                tax
            ) for tax, amounts in res]
        return result

    @api.model
    def resign_content(self, from_date):
        invoices = self.env['account.move'].search(
            [("state", "in", ["posted"]), ("move_type", "in", ["out_refund", "out_invoice", "in_invoice"]),
             ("invoice_date", ">=", from_date)],
            order="system_entry_date asc,sequence_number asc")
        if invoices:
            invoices.write({"hash": "", "hash_control": "", "hash_to_sign": ""})
            [inv.write({"hash": "", "hash_control": "", "hash_to_sign": ""}) for inv in invoices]
            for inv in invoices:
                inv.resign(inv)

    def _check_data_invoice(self):
        if self.env['ir.config_parameter'].sudo().get_param('dont_validate_date'):
            return
        if self.move_type in ['out_invoice', 'out_refund']:
            if self.invoice_date > date.today():
                raise ValidationError(_("Não pode criar facturas para uma data superior a data de hoje"))
        if self.invoice_date and self.move_type == "out_invoice" and self.env.user.company_id.country_id.code == "AO" and self.state == 'draft':
            invoices = self.env['account.move'].search(
                [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'),
                 ('journal_id', '=', self.journal_id.id),
                 ('invoice_date', '!=', None),
                 ('company_id', '=', self.company_id.id)],
                order="invoice_date desc", limit=1
            )
            last_invoice_date = invoices.filtered(lambda r: r.invoice_date > self.invoice_date)
            if last_invoice_date:
                raise ValidationError(_("Can not create invoices, whose date is before date %s") % (
                    fields.Date.to_string(last_invoice_date[0].invoice_date)))

    def _check_system_datetime(self):
        if self.env['ir.config_parameter'].sudo().get_param('dont_validate_date'):
            return
        if self.type in ['out_invoice',
                         'out_refund'] and self.env.user.company_id.contry_id.code == "AO" and self.state == 'draft':
            invoices = self.env['account.move'].search(
                [('state', 'in', ['posted']), ('move_type', '=', self.move_type),
                 ('system_entry_date', '!=', None),
                 ('journal_id', '=', self.journal_id.id),
                 ('company_id', '=', self.company_id.id)],
                order="system_entry_date desc", limit=1
            )
            last_system_entry_date = invoices.filtered(lambda r: r.system_entry_date > fields.Datetime.now())
            if last_system_entry_date:
                raise ValidationError(_(
                    "There is a mismatch of the time of your computer and the last invoice created.\n Check if you system date it's correct!"))

    def get_supplier_saft_data(self):

        result = {
            "PurchaseInvoices": {
                "NumberOfEntries": 0,
                "Invoice": []
            }
        }

        invoices = self.filtered(
            lambda r: r.state in ['posted'] and r.move_type in [
                "in_invoice"] and r.company_id.id == self.env.company.id)

        count = 0
        for inv in invoices:
            invoices_supplier = {
                "InvoiceNo": inv.name,
                "Hash": inv.hash,
                "SourceID": inv.user_id.id,
                "Period": int(fields.Date.to_string(inv.invoice_date)[5:7]),
                "InvoiceDate": fields.Date.to_string(inv.invoice_date),
                "PurchaseType": "FT",
                "SupplierID": inv.partner_id.id if inv.partner_id.id else inv.partner_id.ref,
                "DocumentTotals": {
                    "TaxPayable": format(inv.amount_tax, '.2f') if inv.amount_tax else "0.00",
                    "NetTotal": format(inv.amount_untaxed, '.2f'),
                    # TODO: we must review this with invoice in different currency
                    "GrossTotal": format(inv.amount_total, '.2f'),
                    "Currency": {
                        "CurrencyCode": inv.currency_id.name,
                        "CurrencyAmount": inv.amount_total,
                        "ExchangeRate": inv.currency_id.rate if inv.currency_id.rate else 0,
                    } if inv.currency_id.name != 'AOA' else ""
                },
                "WithholdingTax": [{
                    "WithholdingTaxType": tax.saft_tax_type,
                    "WithholdingTaxDescription": tax.name,
                    "WithholdingTaxAmount": round(tax.amount * ((100) / 100), inv.currency_id.decimal_places),
                } for tax in inv.invoice_line_ids.tax_ids.filtered(lambda r: r.saft_tax_type == 'IVA')],

            }
            count += 1
            invoices_supplier = dict_clean_up("", invoices_supplier)
            result["PurchaseInvoices"]["Invoice"].append(invoices_supplier)

        # result["PurchaseInvoices"]["TotalDebit"] = round(total_debit, 2)
        # result["PurchaseInvoices"]["TotalCredit"] = round(total_credit - total_cancelled_invoice, 2)
        result["PurchaseInvoices"]["NumberOfEntries"] = count

        return result

    def get_saft_data(self):
        """
        Returns a list of invoices dictionaries in saft format fields
        :return:
        """
        total_credit = 0
        total_debit = 0
        result = {
            "SalesInvoices": {
                "NumberOfEntries": 0,
                "TotalDebit": 0,
                "TotalCredit": 0,
                "Invoice": [],
            },
        }
        # iva_exemption = self.env.ref("l10n_ao.%s_account_tax_iva_sales_isento_14" % self.env.user.company_id.id)
        # iva_14 = self.env.ref("l10n_ao.%s_account_tax_iva_sales_14" % self.env.user.company_id.id)
        invoices = self.filtered(
            lambda r: r.state in ['posted'] and r.move_type in ["out_invoice",
                                                                "out_refund"] and r.company_id.id == self.env.company.id)
        bug_values = {
            'invoice_no_Tax': [],
            'line_void_product_id': [],
            'empty_exemption_reason': [],
        }

        for inv in invoices:
            if not any(line.tax_ids.filtered(
                    lambda r: (r.saft_tax_code in ['NOR', 'ISE', 'RED', 'OUT', 'INT'] and r.saft_tax_type in ['IVA']) or
                              (r.saft_tax_code == 'NS' and r.saft_tax_type == 'NS')) for line in inv.invoice_line_ids):
                bug_values['invoice_no_Tax'].append(str(inv.name))
            lines = inv.mapped('invoice_line_ids').filtered(lambda l: l.display_type is False)
            for line in lines:
                i_lines = line.tax_ids.filtered(lambda t: t.saft_tax_code == 'ISE' and not t.tax_exemption_reason_id)
                if i_lines:
                    bug_values['empty_exemption_reason'].append(inv.name)
                if not line.product_id:
                    bug_values['line_void_product_id'].append(inv.name)

        bug_values['invoice_no_Tax'] = list(set(bug_values['invoice_no_Tax']))
        bug_values['empty_exemption_reason'] = list((bug_values['empty_exemption_reason']))
        bug_values['line_void_product_id'] = list(dict.fromkeys(bug_values['line_void_product_id']))
        errors = {"1": "", "2": "", "3": ""}
        if bug_values:
            if bug_values.get('invoice_no_Tax'):
                msg = _(
                    "it's not possible to generate SAFT file because the following invoices don't have taxes:\n %s") % (
                              str(bug_values['invoice_no_Tax']) + "\n")
                errors["1"] = msg
            elif bug_values.get('empty_exemption_reason'):
                msg = _(
                    "It is not possible to generate a SAFT file because the invoices that follow have iva exemption but the motive was not added, please add:\n %s") % (
                              str(bug_values['empty_exemption_reason']) + "\n")
                errors["2"] = msg
            elif bug_values.get('line_void_product_id'):
                msg = _(
                    "The lines in these invoices do not have products inserted, you must add the corresponding products for each line that is missing:\n %s") % (
                              str(bug_values['line_void_product_id']) + "\n")
                errors["3"] = msg
            if any(errors.values()):
                raise ValidationError([str(v) + "\n" for v in errors.values()])
        total_cancelled_invoice = 0
        for inv in invoices:
            status_code = 'N'
            inv_refunds = inv.filtered(lambda
                                           r: r.state == 'out_refund:' and r.payment_state == 'paid')  # Todo: devemos verificar qual e o campo que mapea as notas de credito associadas as facturas
            refund_amount_total = sum(inv_refunds.mapped("amount_untaxed"))
            if inv.state == 'paid' and abs(refund_amount_total) == abs(inv.amount_untaxed):
                status_code = 'A'
                total_cancelled_invoice += refund_amount_total
            # elif inv.state == 'paid' and not abs(refund_amount_total):
            #     status_code = 'F',
            #     total_cancelled_invoice += inv.amount_untaxed

            if inv.journal_id.self_billing is True:
                status_code = 'S'
            # TODO: que caso são os documentos produzidos noutra aplicação.
            source_billing = "P"

            invoice_customer = {
                "InvoiceNo": inv.name.replace(" ", " "),  # inv.name[0:3] + "" + inv.name[4:11],
                "DocumentStatus": {
                    "InvoiceStatus": status_code,
                    "InvoiceStatusDate": fields.Datetime.to_string(inv.saft_status_date)[
                                         0:10] + "T" + fields.Datetime.to_string(inv.saft_status_date)[11:20] if
                    inv.saft_status_date else fields.Datetime.to_string(inv.invoice_date)[
                                              0:10] + "T" + fields.Datetime.to_string(inv.invoice_date)[11:20],
                    "Reason": str(inv.name)[0:48] if inv.name else "",
                    "SourceID": inv.user_id.id,
                    "SourceBilling": source_billing,
                },
                "Hash": inv.hash if inv.hash else "",
                "HashControl": inv.hash_control if inv.hash_control else "0",
                "Period": int(fields.Date.to_string(inv.invoice_date)[5:7]),
                "InvoiceDate": fields.Date.to_string(inv.invoice_date),
                "InvoiceType": "NC" if inv.move_type == "out_refund" else "FT",
                "SpecialRegimes": {
                    "SelfBillingIndicator": "1" if inv.journal_id.self_billing else "0",
                    "CashVATSchemeIndicator": "1" if inv.company_id.tax_exigibility else "0",
                    "ThirdPartiesBillingIndicator": "0",
                },
                "SourceID": inv.user_id.id,
                "EACCode": "",
                "SystemEntryDate": fields.Datetime.to_string(
                    inv.system_entry_date)[0:10] + "T" + fields.Datetime.to_string(inv.system_entry_date)[
                                                         11:20] if inv.system_entry_date else
                fields.Datetime.to_string(inv.create_date)[0:10] + "T" + fields.Datetime.to_string(inv.create_date)[
                                                                         11:20],
                "TransactionID": fields.Date.to_string(inv.invoice_date) + " " + str(inv.journal_id.id).replace(" ",
                                                                                                                "") + " " + str(
                    inv.id),
                "CustomerID": inv.partner_id.id if (
                            inv.partner_id.vat and '999999999' not in inv.partner_id.vat) else '01',
                "ShipTo": "",  # TODO: 4.1.4.15
                "ShipFrom": "",  # TODO: 4.1.4.16
                "MovementEndTime": "",  # TODO: 4.1.4.17,
                "MovementStartTime": "",  # TODO: 4.1.4.18,
                "Line": [{
                    "LineNumber": line.id,
                    "OrderReferences": {
                        "OriginatingON": inv.invoice_origin if inv.invoice_origin else "",  # TODO:4.1.4.19.2.,
                        "OrderDate": "",
                    },
                    "ProductCode": line.product_id.id if line.product_id else "0900107",
                    "ProductDescription": str(line.name)[0:199] if line.name else line.product_id.name[0:199],
                    "Quantity": line.quantity if line.quantity else "0.00",
                    "UnitOfMeasure": line.product_uom_id.name,
                    "UnitPrice": format(line.price_unit * (1 - (line.discount or 0.0) / 100.0), '.4f'),
                    "TaxBase": "",
                    "TaxPointDate": fields.Date.to_string(inv.invoice_date),
                    "References": {
                        "Reference": inv.name,
                        "Reason": str(inv.name)[0:48] if inv.name else "",
                    } if inv.move_type == "out_refund" else "",
                    "Description": line.name[0:199],
                    "ProductSerialNumber": {
                        "SerialNumber": line.product_id.default_code if line.product_id.default_code else "Desconhecido",
                        # TODO: 4.1.4.19.12.
                    },
                    "CreditAmount" if inv.move_type == "out_invoice" else "DebitAmount": line.price_subtotal,
                    "Tax": [{
                        "TaxType": tax.saft_tax_type,
                        "TaxCountryRegion": tax.country_region if tax.country_region else "AO",  # FIXME: 4.1.4.19.15.2.
                        "TaxCode": tax.saft_tax_code,
                        "TaxAmount" if tax.amount_type in ["fixed"] else "TaxPercentage": str(
                            format(tax.amount, '.2f')),
                    } for tax in line.tax_ids if tax.tax_exigibility == "on_invoice"],
                    # todo: verificar o tax_on nos impostos tax.tax_on == "invoice"],
                    "TaxExemptionReason": line.tax_ids.filtered(lambda r: r.amount == 0)[
                                              0].tax_exemption_reason_id.name[
                                          0:59] if line.tax_ids.filtered(
                        lambda
                            r: r.amount == 0) else "",
                    "TaxExemptionCode": line.tax_ids.filtered(lambda r: r.amount == 0)[
                        0].tax_exemption_reason_id.code if line.tax_ids.filtered(lambda r: r.amount == 0) else "",
                    "SettlementAmount": line.discount,
                    "CustomsInformation": {  # TODO: 4.1.4.19.19.
                        "ARCNo": "",
                        "IECAmount": "",
                    },
                } for line in
                    inv.invoice_line_ids.filtered(lambda r: r.display_type not in ['line_note', 'line_section'])],
                "DocumentTotals": {
                    "TaxPayable": format(inv.amount_tax, '.2f') if inv.amount_tax and inv.amount_tax > 0 else "0.00",
                    "NetTotal": format(inv.amount_untaxed, '.2f'),
                    # TODO: we must review this with invoice in different currency
                    "GrossTotal": format(inv.amount_total, '.2f'),
                    # TODO: we must review this with invoice in different currency
                    "Currency": {
                        "CurrencyCode": inv.currency_id.name,
                        "CurrencyAmount": inv.amount_total,
                        "ExchangeRate": round(
                            inv.currency_id._get_conversion_rate(inv.currency_id, inv.company_currency_id,
                                                                 inv.company_id, inv.invoice_date), 2),
                    } if inv.currency_id.name != 'AOA' else "",
                    "Settlement": {
                        "SettlementDiscount": "",
                        "SettlementAmount": "",
                        "SettlementDate": "",
                        "PaymentTerms": inv.invoice_payment_term_id.name if inv.invoice_payment_term_id.name else "",
                    },
                    "Payment": [{
                        "PaymentMechanism": payment.payment_mechanism if payment.payment_mechanism else "OU",
                        "PaymentAmount": payment.amount,
                        "PaymentDate": fields.Date.to_string(
                            payment.date) if payment.date >= inv.invoice_date else inv.invoice_date,
                    } for payment in inv.payment_id]

                },
                "WithholdingTax": [{
                    "WithholdingTaxType": tax.saft_wth_type,
                    "WithholdingTaxDescription": tax.name,
                    "WithholdingTaxAmount": round(tax.amount * ((100) / 100), inv.currency_id.decimal_places),
                } for tax in inv.invoice_line_ids.tax_ids.filtered(lambda r: r.is_withholding)]
                # ["withholding", "captive"])], #todo rever que representa o captive no 14
            }
            invoice_customer = dict_clean_up("", invoice_customer)
            result["SalesInvoices"]["Invoice"].append(invoice_customer)
            total_debit += inv.amount_untaxed if inv.move_type == "out_refund" and inv.state in ["posted"] else 0
            total_credit += inv.amount_untaxed if inv.move_type == "out_invoice" and inv.state in ["posted"] else 0
        result["SalesInvoices"]["TotalDebit"] = round(total_debit, 2)
        result["SalesInvoices"]["TotalCredit"] = round(total_credit - total_cancelled_invoice, 2)

        result["SalesInvoices"]["NumberOfEntries"] = len(invoices)
        return result

    def action_print_receipt(self):
        self.ensure_one()
        move_id = self.env["account.move"].search([('ref', '=', self.name)])
        if move_id.payment_id:
            payment = move_id.payment_id.sorted()[0]
            if payment:
                return self.env.ref('account.action_report_payment_receipt').report_action(payment)

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0
            amount_tax_wth = 0.0

            if move.is_invoice(True):
                for line in move.invoice_line_ids:
                    tax_base_amount_company_currency = 0.0
                    for tax in line.tax_ids:
                        tax_base_amount = line.price_unit * line.quantity
                        if move.currency_id != move.company_id.currency_id:
                            tax_base_amount_company_currency = move.currency_id._convert(tax_base_amount,
                                                                                         move.company_currency_id,
                                                                                         move.company_id, move.date)
                        if tax.tax_exigibility == 'on_payment' and tax.is_withholding and \
                                tax_base_amount_company_currency >= tax.threshold_wht:
                            # Tax amount.
                            tax_amount = tax._compute_amount(
                                line.price_unit * line.quantity * (1 - (line.discount or 0.0) / 100.0),
                                line.price_unit,
                                line.quantity)
                            amount_tax_wth += abs(tax_amount)

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency


                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(
                    sign * move.amount_total)
            move.amount_total_wth = move.amount_total - amount_tax_wth if amount_tax_wth else 0.0

    @contextmanager
    def _sync_unbalanced_lines(self, container):
        yield
        # Skip posted moves.
        for invoice in (x for x in container['records'] if x.state != 'posted'):

            tax_lines = invoice.line_ids.filtered(lambda t: t.tax_line_id and t.tax_line_id.is_withholding)
            if tax_lines:
                return
            # Unlink tax lines if all tax tags have been removed.
            if not invoice.line_ids.tax_ids:
                invoice.line_ids.filtered('tax_line_id').unlink()

            # Set the balancing line's balance and amount_currency to zero,
            # so that it does not interfere with _get_unbalanced_moves() below.
            balance_name = _('Automatic Balancing Line')
            existing_balancing_line = invoice.line_ids.filtered(lambda line: line.name == balance_name)
            if existing_balancing_line:
                existing_balancing_line.balance = existing_balancing_line.amount_currency = 0.0

            # Create an automatic balancing line to make sure the entry can be saved/posted.
            # If such a line already exists, we simply update its amounts.
            unbalanced_moves = self._get_unbalanced_moves({'records': invoice})
            if isinstance(unbalanced_moves, list) and len(unbalanced_moves) == 1:
                dummy, debit, credit = unbalanced_moves[0]
                balance = debit - credit

                vals = {
                    'debit': -balance if balance < 0.0 else 0.0,
                    'credit': balance if balance > 0.0 else 0.0,
                }

                if existing_balancing_line:
                    existing_balancing_line.write(vals)
                else:
                    vals.update({
                        'name': balance_name,
                        'move_id': invoice.id,
                        'account_id': invoice.company_id.account_journal_suspense_account_id.id,
                        'currency_id': invoice.currency_id.id,
                    })
                    container['records'].env['account.move.line'].create(vals)

    def write(self, values):
        res = []
        if self.company_id.country_id.code == "AO":
            for inv in self:
                # inv._check_system_datetime() #Todo: depois devo descomentar e chamar o m�todo check_system_datetime()
                if values.get('state') == "posted" and inv.state == 'draft':
                    if self.company_id.have_invoices == False:
                        self.company_id.sudo().write({'have_invoices': True})
                    self.set_customer_data()
                    inv._check_data_invoice()  # Todo: depois devo descomentar e chamar o m�todo _check_data_invoice()
                    if not inv.company_id.tax_regime_id:
                        raise UserError(
                            _("It is necessary to inform the VAT regime in which your company is in before being able to invoice any customer."))
                    if not inv.system_entry_date:
                        values['system_entry_date'] = fields.Datetime.now()
                    values['saft_status_date'] = fields.Datetime.now()

                    if inv.move_type in ["out_invoice", "out_refund", "in_invoice"] and not inv.hash:
                        if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_tax'):
                            for line in inv.invoice_line_ids.filtered(
                                    lambda r: r.display_type not in ['line_note', 'line_section']):
                                lines_tax = line.tax_ids.filtered(
                                    lambda t: (t.saft_tax_code == 'NOR' and t.saft_tax_type in ['IVA']) or
                                              (t.saft_tax_code in ['NS', 'ISE'] and t.saft_tax_type in ['NS', 'IVA']))
                                lines_tax_exemption = line.tax_ids.filtered(
                                    lambda t: t.saft_tax_code == 'ISE' and not t.tax_exemption_reason_id)

                                if lines_tax_exemption:
                                    raise UserError(
                                        "Porfavor adicione o motivo de isenção no imposto(IVA 0% ou IVA Isenção) para poder proceder com a aprovação da factura.")

                                if not lines_tax:
                                    raise UserError(
                                        _(
                                            "There are lines of invoices without VAT taxes!\n If the product in the line is exempt "
                                            "please add the tax Exemption VAT and in the tax define the reason for Exemption!"))

                        res = super(AccountInvoiceAO, self).write(values)
                        content_hash = inv.get_content_to_sign()
                        values['hash_to_sign'] = content_hash  # todo: devemos descomentar este campo depois
                        content_signed = inv.sign_document(content_hash).split(";")
                        if content_hash != content_signed:
                            values['hash_control'] = content_signed[1] if len(content_signed) > 1 else "0"
                            values['hash'] = content_signed[0]
        res = super(AccountInvoiceAO, self).write(values)
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _check_discount(self):
        if self.env.user.company_id.contry_id.code == "AO":
            for dic in self:
                if dic.discount < 0 or dic.discount > 100:
                    raise ValidationError(_("the discount must be between 0 and 100 %."))
                if dic.price_unit < 0:
                    raise ValidationError(_("the Unit Price must be greater than 0"))
                if dic.quantity < 0:
                    raise ValidationError(_("the quantity value must not be negative"))

    @api.model
    def _get_default_tax_account(self, repartition_line):
        '''AG Override of this method to make the payment account to use the repartition line account_id'''
        tax = repartition_line.invoice_tax_id or repartition_line.refund_tax_id
        if tax.tax_exigibility == 'on_payment' and not self.company_id.country_id.code == "AO":
            account = tax.cash_basis_transition_account_id
        else:
            account = repartition_line.account_id
        return account

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * exchange_partials:    A recorset of all account.partial.reconcile created during the reconciliation
                                        with the exchange difference journal entries.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {'exchange_partials': self.env['account.partial.reconcile']}

        if not self:
            return results

        not_paid_invoices = self.move_id.filtered(lambda move:
                                                  move.is_invoice(include_receipts=True)
                                                  and move.payment_state not in ('paid', 'in_payment')
                                                  )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.account_type not in (
                    'asset_cash', 'liability_credit_card'):
                raise UserError(
                    _("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                    % line.account_id.display_name)
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        sorted_lines = self.sorted(
            key=lambda line: (line.date_maturity or line.date, line.currency_id, line.amount_currency))

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines._all_reconciled_lines()
        involved_partials = involved_lines.matched_credit_ids | involved_lines.matched_debit_ids

        # ==== Create partials ====

        partial_no_exch_diff = bool(
            self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))
        sorted_lines_ctx = sorted_lines.with_context(
            no_exchange_difference=self._context.get('no_exchange_difference') or partial_no_exch_diff)
        partials = sorted_lines_ctx._create_reconciliation_partials()
        results['partials'] = partials
        involved_partials += partials
        exchange_move_lines = partials.exchange_move_id.line_ids.filtered(lambda line: line.account_id == account)
        involved_lines += exchange_move_lines
        exchange_diff_partials = exchange_move_lines.matched_debit_ids + exchange_move_lines.matched_credit_ids
        involved_partials += exchange_diff_partials
        results['exchange_partials'] += exchange_diff_partials

        # ==== Create entries for cash basis taxes ====
        # AG: Alteração pare não aplicar o cash basis.
        is_cash_basis_needed = account.company_id.tax_exigibility and account.account_type in (
            'asset_receivable', 'liability_payable')
        if self.company_id.country_id.code != "AO":
            if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
                tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
                results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        def is_line_reconciled(line, has_multiple_currencies):
            # Check if the journal item passed as parameter is now fully reconciled.
            return line.reconciled \
                or (line.company_currency_id.is_zero(line.amount_residual)
                    if has_multiple_currencies
                    else line.currency_id.is_zero(line.amount_residual_currency)
                    )

        has_multiple_currencies = len(involved_lines.currency_id) > 1
        if all(is_line_reconciled(line, has_multiple_currencies) for line in involved_lines):
            # ==== Create the exchange difference move ====
            # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
            # when importing a full accounting including the reconciliation like Winbooks.

            exchange_move = self.env['account.move']
            caba_lines_to_reconcile = None
            if not self._context.get('no_exchange_difference'):
                # In normal cases, the exchange differences are already generated by the partial at this point meaning
                # there is no journal item left with a zero amount residual in one currency but not in the other.
                # However, after a migration coming from an older version with an older partial reconciliation or due to
                # some rounding issues (when dealing with different decimal places for example), we could need an extra
                # exchange difference journal entry to handle them.
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                exchange_max_date = date.min
                for line in involved_lines:
                    if not line.company_currency_id.is_zero(line.amount_residual):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual': line.amount_residual})
                    elif not line.currency_id.is_zero(line.amount_residual_currency):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual_currency': line.amount_residual_currency})
                    exchange_max_date = max(exchange_max_date, line.date)
                exchange_diff_vals = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    company=involved_lines[0].company_id,
                    exchange_date=exchange_max_date,
                )

                # Exchange difference for cash basis entries.
                if is_cash_basis_needed:
                    caba_lines_to_reconcile = involved_lines._add_exchange_difference_cash_basis_vals(
                        exchange_diff_vals)

                # Create the exchange difference.
                if exchange_diff_vals['move_vals']['line_ids']:
                    exchange_move = involved_lines._create_exchange_difference_move(exchange_diff_vals)
                    if exchange_move:
                        exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                        # Track newly created lines.
                        involved_lines += exchange_move_lines

                        # Track newly created partials.
                        exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                                 + exchange_move_lines.matched_credit_ids
                        involved_partials += exchange_diff_partials
                        results['exchange_partials'] += exchange_diff_partials

            # ==== Create the full reconcile ====
            results['full_reconcile'] = self.env['account.full.reconcile'].create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [(6, 0, involved_partials.ids)],
                'reconciled_line_ids': [(6, 0, involved_lines.ids)],
            })

            # === Cash basis rounding autoreconciliation ===
            # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
            # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)

            if caba_lines_to_reconcile:
                for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                    if not account.reconcile:
                        continue

                    exchange_line = exchange_move.line_ids.filtered(
                        lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                    )

                    (exchange_line + amls_to_reconcile).filtered(lambda l: not l.reconciled).reconcile()

        not_paid_invoices.filtered(lambda move:
                                   move.payment_state in ('paid', 'in_payment')
                                   )._invoice_paid_hook()

        return results

    def _create_exchange_difference_move(self):
        ''' Create the exchange difference journal entry on the current journal items.
        :return: An account.move record.
        '''

        def _add_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
            in order to fix the residual amounts and add them into 'exchange_diff_move_vals'.

            1) When reconciled on the same foreign currency, the journal items are
            fully reconciled regarding this currency but it could be not the case
            of the balance that is expressed using the company's currency. In that
            case, we need to create exchange difference journal items to ensure this
            residual amount reaches zero.

            2) When reconciled on the company currency but having different foreign
            currencies, the journal items are fully reconciled regarding the company
            currency but it's not always the case for the foreign currencies. In that
            case, the exchange difference journal items are created to ensure this
            residual amount in foreign currency reaches zero.

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            :return:                        A list of pair <line, sequence> to perform the reconciliation
                                            at the creation of the exchange difference move where 'line'
                                            is the account.move.line to which the 'sequence'-th exchange
                                            difference line will be reconciled with.
            '''
            journal = self.env['account.journal'].browse(exchange_diff_move_vals['journal_id'])
            to_reconcile = []

            for line in lines:

                exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], line.date)

                if not line.company_currency_id.is_zero(line.amount_residual):
                    # amount_residual_currency == 0 and amount_residual has to be fixed.

                    if line.amount_residual > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id

                elif line.currency_id and not line.currency_id.is_zero(line.amount_residual_currency):
                    # amount_residual == 0 and amount_residual_currency has to be fixed.

                    if line.amount_residual_currency > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id
                else:
                    continue

                sequence = len(exchange_diff_move_vals['line_ids'])
                exchange_diff_move_vals['line_ids'] += [
                    (0, 0, {
                        'name': _('Currency exchange rate difference'),
                        'debit': -line.amount_residual if line.amount_residual < 0.0 else 0.0,
                        'credit': line.amount_residual if line.amount_residual > 0.0 else 0.0,
                        'amount_currency': -line.amount_residual_currency,
                        'account_id': line.account_id.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence,
                    }),
                    (0, 0, {
                        'name': _('Currency exchange rate difference'),
                        'debit': line.amount_residual if line.amount_residual > 0.0 else 0.0,
                        'credit': -line.amount_residual if line.amount_residual < 0.0 else 0.0,
                        'amount_currency': line.amount_residual_currency,
                        'account_id': exchange_line_account.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence + 1,
                    }),
                ]

                to_reconcile.append((line, sequence))

            return to_reconcile

        def _add_cash_basis_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
            in order to fix the cash basis lines using the transfer account in a multi-currencies
            environment when this account is not a reconcile one.

            When the tax cash basis journal entries are generated and all involved
            transfer account set on taxes are all reconcilable, the account balance
            will be reset to zero by the exchange difference journal items generated
            above. However, this mechanism will not work if there is any transfer
            accounts that are not reconcile and we are generating the cash basis
            journal items in a foreign currency. In that specific case, we need to
            generate extra journal items at the generation of the exchange difference
            journal entry to ensure this balance is reset to zero and then, will not
            appear on the tax report leading to erroneous tax base amount / tax amount.

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            '''
            for move in lines.move_id:
                account_vals_to_fix = {}

                move_values = move._collect_tax_cash_basis_values()

                # The cash basis doesn't need to be handle for this move because there is another payment term
                # line that is not yet fully paid.
                if not move_values or not move_values['is_fully_paid']:
                    continue

                # ==========================================================================
                # Add the balance of all tax lines of the current move in order in order
                # to compute the residual amount for each of them.
                # ==========================================================================

                for line in move_values['to_process_lines'].filtered(lambda x: not x.reconciled):

                    vals = {
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'tax_tag_ids': [(6, 0, line._convert_tags_for_cash_basis(line.tax_tag_ids).ids)],
                        'debit': line.debit,
                        'credit': line.credit,
                    }

                    if line.tax_repartition_line_id:
                        # Tax line.
                        grouping_key = self.env[
                            'account.partial.reconcile']._get_cash_basis_tax_line_grouping_key_from_record(line)
                        if grouping_key in account_vals_to_fix:
                            debit = account_vals_to_fix[grouping_key]['debit'] + vals['debit']
                            credit = account_vals_to_fix[grouping_key]['credit'] + vals['credit']
                            balance = debit - credit

                            account_vals_to_fix[grouping_key].update({
                                'debit': balance if balance > 0 else 0,
                                'credit': -balance if balance < 0 else 0,
                                'tax_base_amount': account_vals_to_fix[grouping_key][
                                                       'tax_base_amount'] + line.tax_base_amount,
                            })
                        else:
                            account_vals_to_fix[grouping_key] = {
                                **vals,
                                'account_id': line.account_id.id,
                                'tax_base_amount': line.tax_base_amount,
                                'tax_repartition_line_id': line.tax_repartition_line_id.id,
                            }
                    elif line.tax_ids:
                        # Base line.
                        account_to_fix = line.company_id.account_cash_basis_base_account_id
                        if not account_to_fix:
                            continue

                        grouping_key = self.env[
                            'account.partial.reconcile']._get_cash_basis_base_line_grouping_key_from_record(line,
                                                                                                            account=account_to_fix)

                        if grouping_key not in account_vals_to_fix:
                            account_vals_to_fix[grouping_key] = {
                                **vals,
                                'account_id': account_to_fix.id,
                            }
                        else:
                            # Multiple base lines could share the same key, if the same
                            # cash basis tax is used alone on several lines of the invoices
                            account_vals_to_fix[grouping_key]['debit'] += vals['debit']
                            account_vals_to_fix[grouping_key]['credit'] += vals['credit']

                # ==========================================================================
                # Subtract the balance of all previously generated cash basis journal entries
                # in order to retrieve the residual balance of each involved transfer account.
                # ==========================================================================

                cash_basis_moves = self.env['account.move'].search([('tax_cash_basis_move_id', '=', move.id)])
                for line in cash_basis_moves.line_ids:
                    grouping_key = None
                    if line.tax_repartition_line_id:
                        # Tax line.
                        grouping_key = self.env[
                            'account.partial.reconcile']._get_cash_basis_tax_line_grouping_key_from_record(
                            line,
                            account=line.tax_line_id.cash_basis_transition_account_id,
                        )
                    elif line.tax_ids:
                        # Base line.
                        grouping_key = self.env[
                            'account.partial.reconcile']._get_cash_basis_base_line_grouping_key_from_record(
                            line,
                            account=line.company_id.account_cash_basis_base_account_id,
                        )

                    if grouping_key not in account_vals_to_fix:
                        continue

                    account_vals_to_fix[grouping_key]['debit'] -= line.debit
                    account_vals_to_fix[grouping_key]['credit'] -= line.credit

                # ==========================================================================
                # Generate the exchange difference journal items:
                # - to reset the balance of all transfer account to zero.
                # - fix rounding issues on the tax account/base tax account.
                # ==========================================================================

                for values in account_vals_to_fix.values():
                    balance = values['debit'] - values['credit']

                    if move.company_currency_id.is_zero(balance):
                        continue

                    if values.get('tax_repartition_line_id'):
                        # Tax line.
                        tax_repartition_line = self.env['account.tax.repartition.line'].browse(
                            values['tax_repartition_line_id'])
                        account = tax_repartition_line.account_id or self.env['account.account'].browse(
                            values['account_id'])

                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'account_id': account.id,
                                'sequence': sequence,
                            }),
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': -balance if balance < 0.0 else 0.0,
                                'credit': balance if balance > 0.0 else 0.0,
                                'account_id': values['account_id'],
                                'tax_ids': [],
                                'tax_tag_ids': [],
                                'tax_repartition_line_id': False,
                                'sequence': sequence + 1,
                            }),
                        ]
                    else:
                        # Base line.
                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'sequence': sequence,
                            }),
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': -balance if balance < 0.0 else 0.0,
                                'credit': balance if balance > 0.0 else 0.0,
                                'tax_ids': [],
                                'tax_tag_ids': [],
                                'sequence': sequence + 1,
                            }),
                        ]

        if not self:
            return self.env['account.move']

        company = self[0].company_id
        journal = company.currency_exchange_journal_id

        exchange_diff_move_vals = {
            'move_type': 'entry',
            'date': date.min,
            'journal_id': journal.id,
            'line_ids': [],
        }

        # Fix residual amounts.
        to_reconcile = _add_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # Fix cash basis entries.
        # FIXME: This was changed because Odoo is using a very naive way to evaluate if
        # cash basis is needed and for our case we need to use this for support of tax on payment
        if self.company_id.country_id.code != "AO":
            is_cash_basis_needed = self[0].account_internal_type in ('receivable', 'payable')
            if is_cash_basis_needed:
                _add_cash_basis_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # ==========================================================================
        # Create move and reconcile.
        # ==========================================================================

        if exchange_diff_move_vals['line_ids']:
            # Check the configuration of the exchange difference journal.
            if not journal:
                raise UserError(
                    _("You should configure the 'Exchange Gain or Loss Journal' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.expense_currency_exchange_account_id:
                raise UserError(
                    _("You should configure the 'Loss Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.income_currency_exchange_account_id.id:
                raise UserError(
                    _("You should configure the 'Gain Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))

            exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], company._get_user_fiscal_lock_date())

            exchange_move = self.env['account.move'].create(exchange_diff_move_vals)
        else:
            return None

        # Reconcile lines to the newly created exchange difference journal entry by creating more partials.
        partials_vals_list = []
        for source_line, sequence in to_reconcile:
            exchange_diff_line = exchange_move.line_ids[sequence]

            if source_line.company_currency_id.is_zero(source_line.amount_residual):
                exchange_field = 'amount_residual_currency'
            else:
                exchange_field = 'amount_residual'

            if exchange_diff_line[exchange_field] > 0.0:
                debit_line = exchange_diff_line
                credit_line = source_line
            else:
                debit_line = source_line
                credit_line = exchange_diff_line

            partials_vals_list.append({
                'amount': abs(source_line.amount_residual),
                'debit_amount_currency': abs(debit_line.amount_residual_currency),
                'credit_amount_currency': abs(credit_line.amount_residual_currency),
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

        self.env['account.partial.reconcile'].create(partials_vals_list)

        return exchange_move

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids.filtered(lambda t: not t.invoice_not_affected):
                taxes = line.tax_ids.filtered(lambda t: not t.invoice_not_affected)
                taxes_res = taxes.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal
