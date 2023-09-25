from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dicttoxml2 import dicttoxml
from xml.dom.minidom import parseString
import datetime
from odoo.exceptions import ValidationError, UserError


class L10nAOSaftWizard(models.TransientModel):
    _name = "l10nao.saft.wizard"
    _description = "Estes modelo representa o wizard de exportação do ficheiro SAFT_AO"

    @api.model
    def _default_company(self):
        return self.env.company.id

    @api.model
    def _get_first_day(self):
        end_date = datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)
        date_start = datetime.datetime.now().replace(day=1) - datetime.timedelta(days=end_date.day)
        return date_start

    company_id = fields.Many2one(comodel_name="res.company", string="Companhia", required=True,
                                 default=_default_company, )

    type = fields.Selection(string="File Type",
                            selection=[('I', 'Contablidade integrada com a facturação'),
                                       ('C', 'Contabilidade'),
                                       ('F', 'Facturação'),
                                       # ('P', 'Facturação Parcial'),
                                       ('R', 'Recibos'),
                                       # ('S', 'Auto-Facturação'), # adicionar este elemento ao módulo l10n_ao_autoinvoice
                                       ('A', 'Aquisição de bens e serviços'),
                                       ('Q', 'Aquisição de bens e serviços integrada com a facturação')],
                            help="Tipo de ficheiro")
    date_end = fields.Date("Date End",default=datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1))
    date_start = fields.Date("Date Start",default=_get_first_day)
    comments = fields.Char("Comment")


    def get_pos_saft(self, invoice_saft):
        return invoice_saft

    def get_pos_partners(self):
        return self.env["res.partner"]

    def get_pos_products(self):
        return self.env['product.product']

    def get_pos_taxes(self):
        return self.env['account.tax']

    @api.constrains('date_start', 'date_end')
    def check_dates(self):
        if self.date_start > self.date_end:
            raise ValidationError('Start Date must be lower than End Date')

    def helper_funct(self, parent):
        if parent == "GeneralLedgerAccounts":
            return "Account"
        if parent == "Product":
            return "Product"  # { 'name': parent, 'should_fold': False }
        if parent == "Supplier":
            return "Supplier"
        if parent == "TaxTable":
            return "TaxTable"

    def create_saft_xml(self):

        if not self.company_id.vat:
            raise ValidationError(_("Cannot Generate SAFT data without Company NIF!"))
        if not self.company_id.company_registry:
            raise ValidationError(_("Cannot Generate SAFT data without Company Registry!"))


        header = {
            "AuditFileVersion": self.company_id.audit_file_version,
            "CompanyID": str(self.company_id.company_registry)[0:49] if self.company_id.company_registry else " ",
            "TaxRegistrationNumber": self.company_id.vat if self.company_id.vat else "",
            "TaxAccountingBasis": self.type,
            "CompanyName": self.company_id.name,
            "BusinessName": self.company_id.partner_id.industry_id.name if self.company_id.partner_id.industry_id.name
            else self.company_id.name,
            "CompanyAddress": {
                # "BuildingNumber": "","
                "StreetName": self.company_id.partner_id.street if self.company_id.partner_id.street else "",
                "AddressDetail": str(self.company_id.partner_id.contact_address)[0:80],
                "City": self.company_id.partner_id.city,
                "PostalCode": self.company_id.partner_id.zip if self.company_id.partner_id.zip else "",
                "Province": self.company_id.partner_id.state_id.name if self.company_id.partner_id.state_id.name else "Desconhecido",
                "Country": str(self.company_id.partner_id.country_id.code)[0:2] if self.company_id.partner_id.country_id.code else "Desconhecido"
            },
            "FiscalYear": int(fields.Date.to_string(self.date_start)[0:4]),
            "StartDate": fields.Date.to_string(self.date_start),
            "EndDate": fields.Date.to_string(self.date_end),
            "CurrencyCode": self.company_id.currency_id.name,
            "DateCreated": fields.Date.to_string(fields.Date.today()),
            "TaxEntity": "Global",
            "ProductCompanyTaxID": self.company_id.product_company_tax_id,
            "SoftwareValidationNumber": self.company_id.software_validation_number,
            "ProductID": self.company_id.product_id,
            "ProductVersion": self.company_id.product_version,
            "HeaderComment": self.comments,
            "Telephone": self.company_id.phone and self.company_id.phone[0:19] or '',
            # "Fax": "",
            "Email": self.company_id.email,
            "Website": self.company_id.website if self.company_id.website else "Desconhecido",
        }

        saft_dict = {
            "Header": header,
            "MasterFiles": "",
            "GeneralLedgerEntries": "",
            "SourceDocuments": "",
        }

        source_documents = {

            "SalesInvoices": "",
            "MovementOfGoods": "",
            "WorkingDocuments": "",
            "Payments": "",
            "PurchaseInvoices": "",
        }

        master_files = {
            "GeneralLedgerAccounts": "",
            "Customer": "",
            "Supplier": "",
            "Product": "",
            "TaxTable": "",
        }

        partners = self.env["res.partner"]
        suppliers = self.env["res.partner"]
        taxes = self.env["account.tax"]
        journals = self.env["account.journal"]
        products = self.env["product.product"]

        invoices = self.env["account.move"].search(
            [("invoice_date", ">=", fields.Date.to_string(self.date_start)),
             ("invoice_date", "<=", fields.Date.to_string(self.date_end)),
             ("system_entry_date", "!=", None),
             ("state", "in", ["posted"])], order="system_entry_date asc")

        if self.type in ["A"]:
            invoices = self.env["account.move"].search(
                [("invoice_date", ">=", fields.Date.to_string(self.date_start)),
                 ("invoice_date", "<=", fields.Date.to_string(self.date_end)),
                 ("system_entry_date", "!=", None),
                 ("move_type", "in", ["in_invoice"])], order="system_entry_date asc")
            accounts = self.env["account.account"].search([])
            account_account = accounts.with_context(start_date=self.date_start,
                                                    end_date=self.date_end)
            partners |= invoices.mapped("partner_id")
            master_files["Customer"] = partners.get_saft_data().get("Customer")
            invoices_lines_taxes = invoices.mapped("invoice_line_ids")
            taxes |= invoices_lines_taxes.mapped("tax_ids")
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")
            master_files["GeneralLedgerAccounts"] = account_account.get_saft_data().get("GeneralLedgerAccounts")
            master_files["Supplier"] = partners.get_saft_data().get("Supplier")
            source_documents["PurchaseInvoices"] = invoices.get_supplier_saft_data().get("PurchaseInvoices")
            saft_dict['SourceDocuments'] = source_documents
            [source_documents.pop(keys) for keys in
             ["SalesInvoices", "Payments", "MovementOfGoods", "WorkingDocuments"]]
            master_files.pop("Customer")
            master_files.pop("Product")
            saft_dict.pop("GeneralLedgerEntries")
            master_files.pop("GeneralLedgerAccounts")

            # saft_dict["SourceDocuments"]["Invoices"] = invoices.get_saft_data().get("Invoices")

        if self.type in ["R", "F"]:
            invoices = invoices.filtered(lambda r: r.move_type in ['out_invoice', 'out_refund'])
            partners |= invoices.mapped("partner_id")
            if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_pos'):
                value = self.get_pos_partners()
                partners |= self.get_pos_partners() if self.get_pos_partners() != None else self.env['res.partner']
            master_files["Customer"] = partners.get_saft_data().get("Customer")
            master_files["Product"] = products.get_saft_data().get("Product")
            invoices_taxes = invoices.mapped("invoice_line_ids")
            taxes |= invoices_taxes.mapped("tax_ids")
            taxes = taxes.filtered(lambda r: r.saft_tax_type in ['IVA', 'IS', 'NS'] and r.is_withholding == False)
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")

            if self.type in ["R"]:
                master_files.pop("GeneralLedgerAccounts")
                master_files.pop("Supplier")
                saft_dict.pop("GeneralLedgerEntries")

        if self.type in ["F", "I", "Q"]:
            invoices = self.env["account.move"].search(
                [("invoice_date", ">=", fields.Date.to_string(self.date_start)),("system_entry_date", "!=", None), #TODO: DEVEMOS INCLUIR O SYSTEM_ENTRY DATE NA PESUQISA
                 ("invoice_date", "<=", fields.Date.to_string(self.date_end)),("state","in",["posted"]),("move_type","in",["out_invoice","out_refund"])], order="system_entry_date asc")


            if self.type == "S":
                invoices = invoices.filtered(lambda r: r.journal_id.self_billing and r.move_type in ["in_invoice"] and
                                                       r.partner_id.self_billing_s)

            customer_invoices = invoices.filtered(lambda r: r.move_type in ["out_invoice", "out_refund"])
            supplier_invoices = invoices.filtered(lambda r: r.move_type in ["in_invoice", "in_refund"])
            partners |= customer_invoices.mapped("partner_id")
            suppliers |= supplier_invoices.mapped("partner_id")
            products |= invoices.mapped("invoice_line_ids.product_id")
            if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_pos'):
                products |= self.get_pos_products() if self.get_pos_products() != None else self.env['product.product']
            customer_taxes = customer_invoices.mapped("invoice_line_ids.tax_ids")
            supplier_taxes = supplier_invoices.mapped("invoice_line_ids.tax_ids")
            customer_taxes = customer_taxes.filtered(
                lambda r: r.saft_tax_type in ['IVA', 'IS', 'NS'] and r.is_withholding == False)
            supplier_taxes = supplier_taxes.filtered(
                lambda r: r.saft_tax_type in ['IVA', 'IS', 'NS']  and r.is_withholding == False)

            if self.type == "Q":
                master_files.pop("GeneralLedgerAccounts")
                saft_dict.pop("GeneralLedgerEntries")
                source_documents["PurchaseInvoices"] = invoices.get_supplier_Saft_data().get("PurchaseInvoices")
                taxes = supplier_taxes

            if self.type == "S":
                invoices = invoices.filtered(lambda r: r.journal_id.self_billing and r.type in ["in_invoice"] and
                                                       r.partner_id.self_billing_s)
            if self.type in ["F"]:
                source_documents["SalesInvoices"] = invoices.get_saft_data().get("SalesInvoices")
                if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_pos'):
                    source_documents["SalesInvoices"] = self.get_pos_saft(source_documents["SalesInvoices"])
                [source_documents.pop(keys) for keys in
                 ["PurchaseInvoices", "Payments", "MovementOfGoods", "WorkingDocuments"]]
                # source_documents["PurchaseInvoices"] = invoices.get_supplier_saft_data().get("PurchaseInvoices")
                # source_documents["Payments"] = payments.get_saft_data().get("Payments")
                taxes |= self.get_pos_taxes() if self.get_pos_taxes() != None else self.env['account.tax']
                taxes |= customer_taxes
                if source_documents["SalesInvoices"]["NumberOfEntries"] == 0:
                    raise UserError("Não existem facturas emitidas para o periodo em que está a tentar extrair o ficheiro SAFT,\nporfavor verifique as suas entradas para este mês.")
                saft_dict["SourceDocuments"] = source_documents


            master_files["Product"] = products.get_saft_data().get("Product")
            master_files["Customer"] = [{'CustomerID': '01', 'AccountID': '31.1.2.1', 'CustomerTaxID': '999999999',
                                         'CompanyName': 'CONSUMIRDOR FINAL',
                                         'BillingAddress': {'StreetName': 'Desconhecido',
                                                            'AddressDetail': 'Desconhecido', 'City': 'Luanda',
                                                            'PostalCode': 'Desconhecido', 'Province': 'Desconhecido',
                                                            'Country': 'AO'},
                                         'ShipToAddress': {'StreetName': 'Desconhecido',
                                                           'AddressDetail': 'Desconhecido', 'City': 'Luanda',
                                                           'PostalCode': 'Desconhecido', 'Province': 'Desconhecido',
                                                           'Country': 'AO'}, 'Telephone': '000000000',
                                         'Email': 'Desconhecido', 'Website': 'Desconhecido',
                                         'SelfBillingIndicator': '0'}]
            partners_with_vat = partners.filtered(lambda p: p.vat and '999999999' not in p.vat)
            master_files["Customer"].extend(partners_with_vat.get_saft_data().get("Customer"))
            master_files["Supplier"] = suppliers.get_saft_data().get(
                "Supplier")  # if suppliers.get_saft_data().get("Supplier") else ""
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")

            saft_dict["SourceDocuments"] = source_documents
            if self.type == "F":
                master_files.pop("GeneralLedgerAccounts")
                saft_dict.pop("GeneralLedgerEntries")
                master_files.pop("Supplier")

        if self.type in ["C", "I"]:
            accounts = self.env["account.account"].search([])
            account_account = accounts.with_context(start_date=self.date_start,
                                                    end_date=self.date_end)

            partners |= account_account.get_saft_data().get("customers")
            partners |= account_account.get_saft_data().get("suppliers")
            taxes |= account_account.get_saft_data().get("taxes")
            journals |= account_account.get_saft_data().get("journals")

            master_files["Customer"] = partners.get_saft_data().get("Customer")
            master_files["Supplier"] = partners.get_saft_data().get("Supplier")
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")
            master_files["GeneralLedgerAccounts"] = {
                "Account": account_account.get_saft_data().get("GeneralLedgerAccounts")}
            saft_dict["GeneralLedgerEntries"] = journals.with_context(start_date=self.date_start,
                                                                      end_date=self.date_end).get_saft_data().get(

                "GeneralLedgerEntries")

        saft_dict["MasterFiles"] = master_files

        saft_xml = dicttoxml(saft_dict, custom_root="AuditFile", attr_type=False, item_func=self.helper_funct,
                             fold_list=False)

        dom = str(saft_xml, 'utf-8')
        dom = parseString(dom).toprettyxml()

        saft_file_data = {

            "name": "SAFT_AO_%s_%s_PERIOD_%s-%s" % (fields.Date.to_string(self.date_start)[0:4], self.type,
                                                    fields.Date.to_string(self.date_start)[5:7],
                                                    fields.Date.to_string(self.date_end)[5:7]),
            "audit_file_version": self.company_id.audit_file_version,
            "tax_account_Basis": self.type,
            "company_id": self.company_id.id,
            "fiscal_year": int(fields.Date.to_string(fields.Date.today())[0:4]),
            "date_start": fields.Date.to_string(self.date_start),
            "date_end": fields.Date.to_string(self.date_end),
            "product_company_tax_id": self.company_id.product_company_tax_id,
            "software_validation_number": self.company_id.software_validation_number,
            "product_id": self.company_id.product_id,
            "Product_version": self.company_id.product_version,
            "header_comment": self.comments,
            "text": dom.replace("–", "-").replace("<AuditFile>",
                                              '<AuditFile xmlns:ns="urn:OECD:StandardAuditFile-Tax:AO_1.01_01" xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.01_01">').replace('<?xml version="1.0" ?>','<?xml version="1.0" encoding="UTF-8" ?>'),
            "user_id": self.env.user.id,
        }

        saft_file = self.env["l10nao.saft.file"].create(saft_file_data)
        # saft_file.action_validate()
        action = self.sudo().env.ref('l10n_ao.l10n_saft_file_action').read()[0]
        action['views'] = [(self.env.ref('l10n_ao.l10nao_saft_file_view').id, 'form')]
        action['res_id'] = saft_file.id
        return action
