# -*- coding: utf-8 -*-
from ..models import utils
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from copy import deepcopy
from collections import defaultdict
from odoo.tools import float_repr
from odoo import api, fields, models, release, _
from pprint import pprint
from datetime import datetime

file_types = [
    ('F', 'Facturação'),
    ('A', 'Aquisição de bens e serviços'),
]


class SafTWizard(models.TransientModel):
    _inherit = "account.general.ledger.report.handler"
    _name = "saft.ao.wizard"
    _description = "Generate XML File"

    type = fields.Selection(
        string="File Type", selection=file_types, help="Tipo do ficheiro de exportação")
    comment = fields.Text("Comment")
    company_id = fields.Many2one(string="Company", comodel_name="res.company", required=True,
                                 default=lambda l: l.env.user.company_id)
    date_from = fields.Date("Start Date")
    date_to = fields.Date("End Date")
    content_xml = fields.Text("")
    name = fields.Char("Name", compute='_compute_name')
    status = fields.Datetime.now(),

    @api.depends('date_to', 'date_from')
    def _compute_name(self):
        self.name = "XML SAF-T AO PERIOD %s - %s" % (
            self.date_to or '/',
            self.date_from or '/'
        )

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError('Start Date must be lower than End Date')

    def get_customer(self):
        customer = self.env['res.partner'].search([('customer', '=', True)])
        return customer

    def print_report_xml(self):
        options = self._get_options()
        return self.get_xml(options)

    def get_movement_article(self):
        articles = self.env['stock.move.line'].search(
            [('state', '=', 'done')])
        return articles

    def get_account_tax(self):
        taxes = self.env['account.tax'].search(
            [('active', '=', True)])
        return taxes

    @staticmethod
    def check_product_type(product_type):
        if product_type in ['service', 'monthly']:
            return 'S'
        return 'P'

    def check_saft_tax(self, tax_lines, tax_mapped):
        _tax = None
        last_tax_amount = 0
        for tax in tax_lines:
            if tax_mapped.count(tax.tax_on) > 1:
                last_tax_amount = 0
                for tax_use in tax_lines.filtered(lambda l: l.tax_on == tax.tax_on):
                    if last_tax_amount == 0:
                        if tax_use.amount >= last_tax_amount:
                            _tax = tax_use
                            last_tax_amount = tax_use.amount
                    else:
                        if tax_use.amount >= last_tax_amount:
                            _tax |= tax_use
                            last_tax_amount = tax_use.amount
            else:
                if _tax:
                    _tax |= tax
                else:
                    _tax = tax
        return _tax

    def get_customer_id(self, customer):
        if not customer.vat:
            final_consumer = self.env['res.partner'].search(
                [('vat', '=', '999999999')])
            if final_consumer:
                customer = final_consumer[0]
        final_consumer = self.env['res.partner'].search([('ref', '=', 'CF')])
        if final_consumer:
            customer = final_consumer[0]
        return customer.ref

    @api.model
    def _fill_saft_report_payments_values(self, options, values):

        result = {
            'payments': {
                "number_of_entries": 0,
                "total_debit": 0,
                "total_credit": 0,
                "payment": [],
            }
        }

        payment_data = {}

        invoices = self.env['account.move'].search([("invoice_date", ">=", options['date']['date_from']),
                                                    ("invoice_date", "<=",
                                                     options['date']['date_to']),
                                                    ('company_id', '=',
                                                     self.env.company.id),
                                                    ('move_type', 'in', [
                                                        'out_invoice']),
                                                    ('state', 'in', ['posted'])],
                                                   order="invoice_date asc")
        payments_ = []
        payments = []
        for inv in invoices:
            for payment_rec in self.env['account.payment'].search([("ref", '=', inv.name)]):
                payments_.append(payment_rec)

        for item in payments_:
            if item.id:
                payments.append(item)

        for payment in payments:
            if payment.id:
                payment_status = 'N'
                if payment.state == 'cancelled':
                    payment_status = 'A'

                lined = payment.mapped("line_ids")

                move = self.env['account.move'].search(
                    [("name", '=', payment.ref)])

                payment_data = {
                    "payment_ref_no": str(payment.receipt_no).replace((str(move.invoice_date).split('-'))[0], '20'),
                    "period": utils.extract_period(move.invoice_date),
                    "transaction_id": "%s %s %s" % (
                        str(move.invoice_date), str(payment.journal_id.code).replace(' ', ''),
                        str(payment.name).replace('/', '').replace(' ', '')),
                    "transaction_date": move.invoice_date,
                    "payment_type": 'RG',
                    "description": 'P ' + str(payment.invoice_line_ids.mapped('move_name')),
                    "system_id": payment.name,
                    "document_status": {
                        "payment_status": payment_status,
                        "payment_status_date": str((payment.system_entry_date).strftime("%Y-%m-%d %H:%M:%S")).replace(
                            ' ',
                            'T') if payment.system_entry_date else str(
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")).replace(
                            ' ',
                            'T'),
                        # "Reason": "",
                        "source_id": payment.create_uid.id,
                        "source_payment": 'P',
                    },
                    "payment_method": {
                        "payment_mechanism": payment.payment_mechanism or 'TB',
                        "payment_amount": utils.gross_total(payment.amount),
                        "payment_date": payment.date,
                    },
                    "source_id": payment.create_uid.id,
                    "system_entry_date": str(payment.system_entry_date).replace(' ',
                                                                                'T') if payment.system_entry_date else str(
                        (payment.write_date).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
                    "customer_id": 'CF',
                    "line": []
                }

                lined_in = self.env['account.move'].search(
                    [("name", '=', payment.ref), ('move_type', 'in', ['out_invoice'])], order="invoice_date asc")

                for line in lined_in.line_ids:
                    if line.tax_ids:
                        lines = {
                            "line_number": line.id,
                            "source_document_id": {
                                "originating_on": payment.name,
                                "invoice_date": move.invoice_date,
                                "description": payment.ref or payment.name,
                            },
                            "settlement_amount": sum(line.mapped("discount")),
                            "taxs": [],

                        }

                        if move.move_type == "out_refund" and move.payment_state in ["not_open", "paid"]:
                            lines["debit_amount"] = move.amount_untaxed
                        elif move.move_type == "out_invoice" and move.payment_state in ["not_open", "paid"]:
                            lines["credit_amount"] = move.amount_untaxed

                        for tax in line.tax_ids:
                            if tax.tax_on == "invoice":
                                lines["taxs"].append({
                                    "tax_type": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS',
                                                                                           'IS'] else "IVA",
                                    # FIXME: 4.1.4.19.15.2.
                                    "tax_country_region": tax.country_region,
                                    "tax_code": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                           'IS'] else tax.saft_tax_code,
                                    'tax_percentage': tax.amount if tax.amount_type in ["percent", "division"] else "0"
                                })

                        for tax in line.tax_ids:
                            if tax.tax_on == "invoice":
                                lines[
                                    "tax_exemption_reason"] = tax.exemption_reason if tax.amount == 0 and tax.exemption_reason else False
                                lines['tax_exemption_code'] = "M21" if tax.amount == 0 else ""
                        payment_data["line"].append(lines)

                payment_data["document_totals"] = {
                    "tax_payable": utils.gross_total(move.amount_tax),
                    "net_total": utils.gross_total(move.amount_untaxed),
                    "gross_total": utils.gross_total(move.amount_total),
                    "settlement": {
                        "settlement_amount": 0.0,
                    },
                }

                if lined.currency_id != lined.company_id.currency_id:
                    payment_data["document_totals"]["currency"] = {
                        "currency_code": lined.currency_id.name,
                        "currency_amount": lined.amount_total,
                        "exchange_rate": lined.currency_id.rate
                    }

                if move.move_type == "out_refund" and move.payment_state in ["not_paid", "paid"]:
                    result["payments"]["total_debit"] += utils.gross_total(
                        move.amount_untaxed)
                elif move.move_type == "out_invoice" and move.payment_state in ["not_paid", "paid"]:
                    result["payments"]["total_credit"] += utils.gross_total(
                        move.amount_untaxed)

            result['payments']['payment'].append(payment_data)
        result['payments']['number_of_entries'] = len(payments)
        # for rec in result['payments']['payment']:
        #     for re in rec['line']:
        #         print(re)
        values.update(result)

    @api.model
    def _fill_saft_report_sales_order_values(self, options, values):

        result = {
            'working_documents': {
                "number_of_entries": 0,
                "total_debit": 0,
                "total_credit": 0,
                "work_documents": [],
            }
        }

        sales = self.env['sale.order'].search([("date_order", ">=", fields.Datetime.from_string(self.date_from)),
                                               ("date_order", "<=", fields.Datetime.from_string(self.date_to)),
                                               ('company_id', '=',
                                                self.env.company.id),
                                               ('state', 'in', [
                                                   'sale'])
                                               ],
                                              order="name asc")
        # for rec in sales:
        #     print()
        #     print(rec.date_order, rec.name, rec.partner_id, rec.user_id, rec.state)

        for sale in sales:
            status_code = 'N'
            if sale.state == 'cancel':
                status_code = 'A'
            if sale.state in ['sale', 'done']:
                status_code = 'F'
            source_billing = "P"
            sale_order = {
                "document_number": sale.work_type + " " + sale.name.split(' ')[-1],
                "document_status": {
                    "work_status": status_code,
                    "work_status_date": str((sale.date_order).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
                    "source_id": sale.user_id.id,
                    "source_billing": source_billing,
                },
                "hash": sale.hash,
                "hash_control": "0" or sale.hash_control,
                "period": utils.extract_period(sale.create_date),
                "work_date": str(sale.date_order)[0:10],
                "work_type": sale.work_type,
                "source_id": sale.user_id.id,
                "system_entry_date": str((sale.system_entry_date.strftime("%Y-%m-%d %H:%M:%S")).replace(' ',
                                                                                                        'T') if sale.system_entry_date else str(
                    sale.date_order.strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T')),
                "customer_id": 'CF',
                "lines": [],
                "document_totals": {
                    "tax_payable": utils.gross_total(sale.amount_tax),
                    "net_total": utils.gross_total(sale.amount_untaxed),
                    "gross_total": utils.gross_total(sale.amount_total),
                }

            }

            for line in sale.order_line:

                lines = {
                    "line_number": line.id,
                    "product_code": line.product_id.id or line.product_id.default_code,
                    "product_description": line.product_id.name[:200],
                    "quantity": line.product_uom_qty,
                    "unit_of_measure": "UN",
                    "unit_price": line.price_unit,
                    "tax_base": line.price_subtotal if line.price_unit == 0.0 else 0.0,
                    "tax_point_date": str(sale.date_order)[0:10],
                    "description": line.product_id.name[:200],
                    "credit_amount": utils.gross_total(line.price_subtotal),
                    "tax_exemption_reason": 0,
                    "taxs": [],
                }

                taxes_to_use = self.check_saft_tax(line.tax_id,
                                                   line.tax_id.mapped('tax_on'))
                if taxes_to_use:
                    for tax in taxes_to_use:
                        if tax.tax_on != 'withholding':
                            tax_values = {
                                "tax_type": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
                                # FIXME: 4.1.4.19.15.2.
                                "tax_country_region": tax.country_region,
                                # "tax_code": tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
                                "tax_code": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                       'IS'] else tax.saft_tax_code,
                            }
                            if tax.amount_type in ["percent", "division"]:
                                tax_values["tax_percentage"] = utils.gross_total(
                                    tax.amount)
                            elif tax.amount_type in ["fixed"]:
                                tax_values["tax_amount"] = utils.gross_total(
                                    tax.amount)
                            if tax.tax_on == "invoice":
                                lines["tax_exemption_reason"] = tax.exemption_reason if tax.amount == 0 else False,
                                lines["tax_exemption_code"] = "M21" if tax.amount == 0 else "",
                            lines["taxs"].append(tax_values)
                if not lines["taxs"]:
                    lines["taxs"].append({
                        "tax_type": "NS",
                        "tax_country_region": "AO",
                        "tax_code": "NS",
                        "tax_percentage": "0"})
                    lines["tax_exemption_reason"] = "Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
                    lines["tax_exemption_code"] = "M21"

                sale_order["lines"].append(lines)

            result['working_documents']["work_documents"].append(sale_order)
            result['working_documents']["total_credit"] += utils.gross_total(
                sale.amount_untaxed)

            result['working_documents']["number_of_entries"] += 1
        values.update(result)

    @api.model
    def _fill_saft_report_products_values(self, options, values):
        res = {
            'product_vals_list': []
        }
        default_product = {
            'product_type': 'S',
            'product_code': 'HS12D',
            'product_group': 'Todos',
            'product_description': 'Serviços',
            'product_number_code': 'HS12D',
            # 'CustomsDetails': product.customs_details or "",
        }

        for product in self.env['product.product'].search([]):
            product_val = {
                'product_type': self.check_product_type(product['type']),
                'product_code': product['id'],
                'product_group': product['categ_id']['name'],
                'product_description': product['description_sale'].strip()[:200] if product['description_sale'] else
                product['name'].strip()[:200],
                'product_number_code': product['default_code'] or product['id'],
                # 'CustomsDetails': product.customs_details or "",
            }
            res['product_vals_list'].append(product_val)
        res['product_vals_list'].append(default_product)

        values.update(res)

    @api.model
    def _fill_saft_report_general_ledger_values(self, options, values):

        result = {
            "sales_invoices": {
                "number_of_entries": 0,
                "total_debit": 0,
                "total_credit": 0,
                "invoices": [],
            },
            "invoices": {
                "number_of_entries": 0,
                "invoices": [],
            },

            # Codigo Acrescentado
            "purchase_invoices": {
                "number_of_entries": 0,
                "invoices": [],
            }
        }
        # Sales Invoicing
        invoices = self.env['account.move'].search([("invoice_date", ">=", self.date_from),
                                                    ("invoice_date", "<=", self.date_to),
                                                    ('move_type', '=', 'out_invoice'),
                                                    ('company_id', '=', self.env.company.id),
                                                    ('state', '=', 'posted'),
                                                    ('payment_state', 'in', ['paid', 'not_paid'])],
                                                   order="invoice_date,name asc")
        print("olha encontraste vendas?", invoices)
        # invoices.clean_number_invoices(self.date_from, self.date_to)
        for inv in invoices:
            status_code = 'N'
            if inv.state == 'cancel':
                status_code = 'A'
            elif inv.journal_id.self_billing is True:
                status_code = 'S'
            source_billing = "P"

            # FACTURAS CLIENTES

            if inv.move_type in ["out_invoice"]:
                invoice_customer = {
                    "invoice_no": inv.name,
                    "document_status": {
                        "invoice_status": status_code,
                        "invoice_status_date": str(inv.system_entry_date).replace(' ',
                                                                                  'T') if inv.system_entry_date else str(
                            inv.create_date).replace(' ', 'T'),
                        # "Reason": "",  # TODO GENERATE CONTENT FOR REASON
                        "source_id": inv.user_id.id,
                        "source_billing": source_billing,
                    },
                    "hash": inv.hash,
                    "hash_control": inv.hash_control,
                    "period": int(str(inv.invoice_date)[5:7]),
                    "invoice_date": inv.invoice_date,
                    "invoice_type": "FT" if inv.move_type == "out_invoice" else "NC",
                    # 'order_references': inv.name,

                    "special_regimes": {
                        "self_billing_indicator": 1 if inv.journal_id.self_billing else 0,
                        "cash_vat_scheme_indicator": 1 if inv.company_id.tax_exigibility else 0,
                        "third_parties_billing_indicator": 0,
                    },
                    "source_id": inv.user_id.id,
                    # "EACCode": "N/A",
                    "system_entry_date": str(inv.system_entry_date).replace(' ', 'T') if inv.system_entry_date else str(
                        inv.create_date).replace(' ', 'T'),
                    "transaction_id": "%s %s %s" % (
                        inv.date, inv.journal_id.code.replace(' ', ''),
                        inv.name.replace(' ', '').replace('/', '')) if inv.name else '',
                    "customer_id": 'CF',
                    # "ShipTo": "",  # TODO: 4.1.4.15
                    # "ShipFrom": "",  # TODO: 4.1.4.16
                    # "MovementEndTime": "",  # TODO: 4.1.4.17,
                    # TODO: 4.1.4.18,
                    "movement_start_time": str(inv.system_entry_date).replace(' ',
                                                                              'T') if inv.system_entry_date else str(
                        inv.create_date).replace(' ', 'T'),
                    "lines": [],
                    "document_totals": {
                        "tax_payable": utils.gross_total(inv.amount_tax),
                        "net_total": utils.gross_total(inv.amount_untaxed),
                        # TODO: we must review this with invoice in different currency
                        "gross_total": utils.gross_total(inv.amount_total),
                        # TODO: we must review this with invoice in different currency
                        "currency": {
                            "currency_code": inv.currency_id.name,
                            "Currency_amount": utils.gross_total(inv.amount_total),
                            "exchange_rate": inv.currency_id.rate,
                        } if inv.currency_id != inv.company_id.currency_id else {},
                        "settlement": {
                            "settlement_discount": inv.settlement_discount or 0,
                            "settlement_amount": inv.settlement_amount or 0,
                            # "SettlementDate": inv.settlement_date or "",
                            "payment_terms": inv.payment_id.name if inv.payment_id.name else "",
                        },
                        "payments": [{
                            "payment_mechanism": payment.payment_mechanism or "TB",
                            "payment_amount": utils.gross_total(payment.amount),
                            "payment_date": payment.payment_date,
                        } for payment in inv.payment_id]

                    },
                    "withholding_tax": [{
                        "withholding_tax_type": tax.tax_id.saft_wth_type,
                        "withholding_tax_description": tax.tax_id.name,
                        "withholding_tax_amount": utils.gross_total(tax.amount),
                    } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")],
                }
                if not invoice_customer['document_totals']['payments']:
                    invoice_customer['document_totals'].pop('payments')

                # payments = []
                # for payment in inv.payment_ids:
                #     payment_values = {
                #         "PaymentMechanism": payment.payment_mechanism,
                #         "PaymentAmount": utils.gross_total(payment.amount),
                #         "PaymentDate": payment.payment_date,
                #     }
                #     payments.append(payment_values)
                # invoice_customer['DocumentTotals']['Payment'] = payments

                for line in inv.invoice_line_ids:
                    lines = {
                        "line_Number": line.id,
                        # "OrderReferences": {"OriginatingON": inv.origin or "", "OrderDate": ""},  # TODO:4.1.4.19.2.
                        "product_code": line.product_id.id if line.product_id else 'HS12D',
                        "product_description": line.product_id.description_sale.strip()[
                                               :200] if line.product_id.description_sale else line.product_id.name.strip()[
                                                                                              :200],
                        "quantity": line.quantity,
                        "unit_of_measure": line.product_uom_id.name,
                        "unit_price": line.price_unit,
                        "tax_base": line.price_subtotal if line.price_unit == 0.0 else 0.0,
                        "tax_point_date": inv.date,
                        "credit_amount": False,
                        "debit_amount": False

                    }

                    if inv.move_type == "out_refund":
                        lines['references'] = {
                            "reference": inv.name,
                        }

                    lines['description'] = line.product_id.name.strip()[:200],
                    # lines['ProductSerialNumber'] = {
                    #     "SerialNumber": line.product_id.default_code or "S/N",  # TODO: 4.1.4.19.12.
                    # }

                    if inv.move_type == "out_refund" and inv.payment_state in ["not_paid", "paid"]:
                        lines["debit_amount"] = utils.gross_total(
                            line.price_subtotal)

                    if inv.move_type == "out_invoice" and inv.payment_state in ["not_paid", "paid"]:
                        lines["credit_amount"] = utils.gross_total(
                            line.price_subtotal)

                    lines["tax"] = []

                    taxes_to_use = self.check_saft_tax(
                        line.tax_ids, line.tax_ids.mapped('tax_on'))
                    if taxes_to_use:
                        for tax in taxes_to_use:
                            if tax.tax_on != 'withholding':
                                tax_values = {
                                    "tax_type": tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS',
                                                                                           'IS'] else "IVA",
                                    # FIXME: 4.1.4.19.15.2.
                                    "tax_country_region": tax.country_region,
                                    # "tax_code": tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
                                    "tax_code": tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS',
                                                                                           'IS'] else tax.saft_tax_code,
                                }
                                if tax.amount_type in ["percent", "division"]:
                                    tax_values["tax_percentage"] = utils.gross_total(
                                        tax.amount)
                                elif tax.amount_type in ["fixed"]:
                                    tax_values["tax_amount"] = utils.gross_total(
                                        tax.amount)
                                if tax.tax_on == "invoice":
                                    if tax.amount == 0:
                                        lines["tax_exemption_reason"] = tax.exemption_reason,
                                        lines["tax_exemption_code"] = "M21" if tax.amount == 0 else " ",
                                lines["tax"].append(tax_values)
                    if not lines["tax"]:
                        lines["tax"].append({"tax_type": "NS",
                                             "tax_country_region": "AO",
                                             "tax_code": "NS",
                                             "tax_percentage": "0"})
                        lines["tax_exemption_reason"] = "Isento nos termos da alínea l) do nº1 do artigo 12.º do CIVA"
                        lines["tax_exemption_code"] = "M21"
                    lines["settlement_amount"] = line.discount
                    # lines["CustomsInformation"] = {  # TODO: 4.1.4.19.19.
                    #     "ARCNo": "",
                    #     "IECAmount": "",
                    # }
                    invoice_customer["lines"].append(lines)

                if inv.currency_id == inv.company_id.currency_id:
                    invoice_customer["document_totals"].pop("currency")

                if not [tax.id for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]:
                    invoice_customer.pop("withholding_tax")

                result["sales_invoices"]["invoices"].append(invoice_customer)

                if inv.move_type == "out_refund":
                    result["sales_invoices"]["total_debit"] += utils.gross_total(
                        inv.amount_untaxed)

                # if is normal or invoiced
                elif inv.move_type == "out_invoice" and inv.payment_state in ["not_paid", "paid"]:
                    result["sales_invoices"]["total_credit"] += utils.gross_total(
                        inv.amount_untaxed)

                result["sales_invoices"]["number_of_entries"] += 1

            else:
                invoice_supplier = {
                    "invoice_no": inv.sequence_number,
                    "source_id": inv.user_id.id,
                    "period": int(str(inv.invoice_date)[5:7]),
                    "invoice_date": inv.invoice_date,
                    "invoice_type": "ND" if inv.move_type == "in_refund" else "FT",
                    "supplier_id": inv.partner_id.ref or inv.partner_id.id,
                    "document_totals": {
                        "tax_payable": utils.gross_total(inv.amount_tax),
                        "net_total": utils.gross_total(inv.amount_untaxed),
                        # TODO: we must review this with invoice in different currency
                        "gross_total": utils.gross_total(inv.amount_total),
                        "deductible": {
                            "tax_base": utils.gross_total(inv.amount_untaxed),
                            # TODO: we must review this with invoice in different currency
                            "deductible_tax": "",
                            "deductible_percentage": "",
                            # "Currency": {
                            # "CurrencyCode": inv.currency_id.name,
                            #  "CurrencyAmount": utils.gross_total(inv.amount_total),
                            #  } if inv.currency_id != inv.company_id.currency_id else {},

                        },
                        "payments": [{
                            "payment_mechanism": payment.payment_mechanism or "TB",
                            "payment_amount": utils.gross_total(payment.amount),
                            "payment_date": payment.payment_date,
                        } for payment in inv.payment_id]

                    },
                    "withholding_tax": [{
                        "withholding_tax_type": tax.tax_id.saft_wth_type,
                        "withholding_tax_description": tax.tax_id.name,
                        "withholding_tax_amount": utils.gross_total(tax.amount),
                    } for tax in inv.tax_line_ids.filtered(lambda r: r.tax_id.tax_on == "withholding")]

                }
                if not invoice_supplier['document_totals']['payments']:
                    invoice_supplier['document_totals'].pop('payments')

                # if inv.currency_id == inv.company_id.currency_id:
                # invoice_supplier["DocumentTotals"].pop("Currency")

                result["invoices"]["invoices"].append(invoice_supplier)
                result["invoices"]["number_of_entries"] += 1
        values.update(result)

    @api.model
    def _fill_saft_report_tax_table_values(self, options, values):
        result = {"tax_table": []}
        control = []

        for tax in self.env['account.tax'].search([('active', '=', True)]):
            if tax.saft_tax_type not in control:
                tax_table = {
                    'tax_type': tax.saft_tax_type if tax.saft_tax_code in ['IVA', 'NS', 'IS'] else "IVA",
                    'tax_country_region': 'AO',
                    # 'tax_code':tax.tax_type if tax.tax_code == 'NS' else tax.tax_code,
                    'tax_code': tax.saft_tax_code if tax.saft_tax_type in ['IVA', 'NS', 'IS'] else tax.saft_tax_code,
                    'description': tax.description,
                    'tax_percentage': tax.amount if tax.amount_type in ["percent",
                                                                        "division"] else "0.0"
                }

                control.append(tax.saft_tax_type)
                result['tax_table'].append(tax_table)
                print(tax_table)
        values.update(result)

    @api.model
    
    def _fill_saft_report_partner_ledger_values(self, options, values):
        res = {
            'customer_vals_list': [],
            'supplier_vals_list': [],
            'partner_detail_map': defaultdict(lambda: {
                'type': False,
                'addresses': [],
                'contacts': [],
            }),
        }

        all_partners = self.env['res.partner']

        # Fill 'customer_vals_list' and 'supplier_vals_list'
        report = self.env.ref('account_reports.partner_ledger_report')
        new_options = report._get_options(options)
        new_options['account_type'] = [
           {'id': 'trade_receivable', 'selected': True},
            {'id': 'non_trade_receivable', 'selected': True},
            {'id': 'trade_payable', 'selected': True},
            {'id': 'non_trade_payable', 'selected': True},
        ]
        handler = self.env['account.partner.ledger.report.handler']
        partners_results = handler._query_partners(new_options)
        partner_vals_list = []
        rslts_array = tuple((partner, res_col_gr[options['single_column_group']]) for partner, res_col_gr in partners_results)
        init_bal_res = handler._get_initial_balance_values(tuple(partner.id for partner, results in rslts_array), options)
        initial_balances_map = {}
        initial_balance_gen = ((partner_id, init_bal_dict.get(options['single_column_group'])) for partner_id, init_bal_dict in init_bal_res.items())

        for partner_id, initial_balance in initial_balance_gen:
            initial_balances_map[partner_id] = initial_balance
        for partner, results in partners_results:
            # Ignore Falsy partner.
            if not partner:
                continue

            all_partners |= partner

            partner_sum = results.get('sum', {})
            partner_init_bal = results.get('initial_balance', {})

            opening_balance = partner_init_bal.get('debit', 0.0) \
                              - partner_init_bal.get('credit', 0.0)
            closing_balance = partner_init_bal.get('debit', 0.0) \
                              + partner_sum.get('debit', 0.0) \
                              - partner_init_bal.get('credit', 0.0) \
                              - partner_sum.get('credit', 0.0)
            partner_vals_list.append({
                'partner': partner,
                'account_id': partner['property_account_receivable_id'],
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })

        if all_partners:
            domain = [('partner_id', 'in', tuple(all_partners.ids))]
            tables, where_clause, where_params = self.env.ref('account_reports.general_ledger_report')._query_get(new_options,'strict_range', domain=domain)
            self._cr.execute(f'''
                SELECT
                    account_move_line.partner_id,
                    SUM(account_move_line.balance)
                FROM {tables}
                JOIN account_account account ON account.id = account_move_line.account_id
                WHERE {where_clause}
                AND account.account_type IN ('asset_receivable', 'liability_payable')
                GROUP BY account_move_line.partner_id
            ''', where_params)

            for partner_id, balance in self._cr.fetchall():
                res['partner_detail_map'][partner_id]['type'] = 'customer' if balance >= 0.0 else 'supplier'

        for partner_vals in partner_vals_list:
            partner_id = partner_vals['partner'].id
            if res['partner_detail_map'][partner_id]['type'] == 'customer':
                res['customer_vals_list'].append(partner_vals)
            elif res['partner_detail_map'][partner_id]['type'] == 'supplier':
                res['supplier_vals_list'].append(partner_vals)

        # Fill 'partner_detail_map'.
        all_partners |= values['company'].partner_id
        partner_addresses_map = defaultdict(dict)
        partner_contacts_map = defaultdict(lambda: self.env['res.partner'])

        def _track_address(current_partner, partner):
            if partner.zip and partner.city:
                address_key = (partner.zip, partner.city)
                partner_addresses_map[current_partner][address_key] = partner

        def _track_contact(current_partner, partner):
            phone = partner.phone or partner.mobile
            if phone:
                partner_contacts_map[current_partner] |= partner

        for partner in all_partners:
            _track_address(partner, partner)
            _track_contact(partner, partner)
            for child in partner.child_ids:
                _track_address(partner, child)
                _track_contact(partner, child)

        no_partner_address = self.env['res.partner']
        no_partner_contact = self.env['res.partner']
        for partner in all_partners:
            res['partner_detail_map'][partner.id].update({
                'partner': partner,
                'addresses': list(partner_addresses_map[partner].values()),
                'contacts': partner_contacts_map[partner],
            })
            if not res['partner_detail_map'][partner.id]['addresses']:
                no_partner_address |= partner
            if not res['partner_detail_map'][partner.id]['contacts']:
                no_partner_contact |= partner

        # if no_partner_address:
        #     raise UserError(_(
        #         "Please define at least one address (Zip/City) for the following partners: %s.",
        #         ', '.join(no_partner_address.mapped('display_name')),
        #     ))
        # if no_partner_contact:
        #     raise UserError(_(
        #         "Please define at least one contact (Phone or Mobile) for the following partners: %s.",
        #         ', '.join(no_partner_contact.mapped('display_name')),
        #     ))

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _prepare_saft_report_values(self, options):
        def format_float(amount, digits=2):
            return float_repr(amount or 0.0, precision_digits=digits)

        def format_date(date_str, formatter):
            date_obj = fields.Date.to_date(date_str)
            return date_obj.strftime(formatter)

        company = self.env.company

        # print("\n\nCompany:.....", company.display_name)

        if not company.company_registry:
            raise UserError(
                _("Please define `Company Registry` for your company."))
            
        options["single_column_group"] = tuple(options["column_groups"].keys())[0]
        
        template_values = {
            'company': company,
            'fiscal_year': company.accounting_year.name,
            'tax_entity': company.tax_entity,
            'xmlns': '',
            'file_version': 'undefined',
            'accounting_basis': 'undefined',
            'today_str': fields.Date.to_string(fields.Date.context_today(self)),
            'software_version': release.version,
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'format_float': format_float,
            'format_date': format_date,
        }

        self._fill_saft_report_general_ledger_values(options, template_values)
        self._fill_saft_report_products_values(options, template_values)
        self._fill_saft_report_tax_table_values(options, template_values)
        self._fill_saft_report_partner_ledger_values(options, template_values)
        self._fill_saft_report_sales_order_values(options, template_values)
        self._fill_saft_report_payments_values(options, template_values)

        return template_values

    def get_xml(self):
        options = self.env.ref('account_reports.general_ledger_report')._get_options()
        options = deepcopy(options)
        # options = self._force_strict_range(options)
        options.pop('multi_company', None)
        options['unfolded_lines'] = []
        options['unfold_all'] = False
        options['date']['date_from'] = self.date_from
        options['date']['date_to'] = self.date_to

        # print("\nGet_xml: .....  . . .. ", options)

        template_vals = self._prepare_saft_report_values(options)

        # print("Template Vals\n")
        # pprint(template_vals)
        # print("\nTemplate Vals: .....  . . .. ",template_vals)

        self.content_xml = self.env['ir.qweb']._render('l10n_ao_saft.saft_report',template_vals)
        self.content_xml = self.content_xml.replace('<AuditFile>',
                                                    """<?xml version="1.0" encoding="utf-8"?>
                      <AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.01_01" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:OECD:StandardAuditFile-Tax:AO_1.01_01 https://raw.githubusercontent.com/assoft-portugal/SAF-T-AO/master/XSD/SAFTAO1.01_01.xsd">""")

        self.content_xml = self.content_xml.strip()


        req = self.download()
        return req

    def download(self):

        print("\nID::", self.id)

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/download/saft_ao_file/%s' % self.id,
            'target': 'new',
        }
