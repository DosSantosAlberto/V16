from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from .saft import dict_clean_up


class AOResPartnerAccountChart(models.Model):
    _inherit = "res.partner"

    # self_billing_c = fields.Boolean("Self Billing Customer", required=False)
    self_billing_s = fields.Boolean("Self Billing Supplier", required=False)

    def get_saft_data(self):
        '''
        Returns all the fields associated to the produtions of SAFT file. Since the
        :return: {"Customer": {"CustomerID": self.ref if self.ref else self.id,
                                  "AccountID": self.property_account_payable_id.code,
                                  "CustomerTaxID": self.vat,
                                  "CompanyName": self.name,
                                  "Contact": "",
                                  "BillingAddress": billing_address,
                                  "ShipToAddress": ship_address,
                                  "Telephone": self.phone if self.phone else "",
                                  "Email": self.email if self.email else "",
                                  "Website": self.website if self.website else "",
                                  "SelfBillingIndicator": "0" if not self.self_billing_c else "1"
                                },
                "SupplierID": {"SupplierID": self.ref if self.ref else self.id,
                                "AccountID": self.property_account_payable_id.code,
                                "CustomerTaxID": self.vat,
                                "CompanyName": self.name,
                                "Contact": "",
                                "BillingAddress": {
                                    "BuildingNumber": "",
                                    "StreetName": record.street,
                                    "AddressDetail": record.contact_address,
                                    "City": record.city,
                                    "PostalCode": record.zip,
                                    "Province": record.state_id.name,
                                    "Country": record.country_id.code
                                },
                                "ShipToAddress":
                                    "BuildingNumber": "",
                                    "StreetName": record.street,
                                    "AddressDetail": record.contact_address,
                                    "City": record.city,
                                    "PostalCode": record.zip,
                                    "Province": record.state_id.name,
                                    "Country": record.country_id.code
                                },,
                                "Telephone": self.phone if self.phone else "",
                                "Email": self.email if self.email else "",billing_address
                                "Website": self.website if self.website else "",
                                "SelfBillingIndicator": "0" if not self.self_billing_s else "1"
                }
        '''
        result = {
            "Customer": [],
            "Supplier": [],
        }

        for partner in self:
            # Validation zone for all fields that are required in SAFT but are not required in odoo model or view.
            # if not partner.vat:
            # raise ValidationError(_("Cannot Generate SAFT data without NIF. Partner %s") % partner.name)
            if not partner.country_id:
                raise ValidationError(_("Cannot Generate SAFT data without Country. Partner %s") % partner.name)
            if not partner.city:
                raise ValidationError(_("Cannot Generate SAFT data without City. Partner %s") % partner.name)

            # invoice_address = partner.child_ids.filtered(lambda r: r.type == "invoice")
            # delivery_address = partner.child_ids.filtered(lambda r: r.type == "invoice")
            record = partner
            # delivery_address = partner.child_ids.filtered(lambda r: r.type == "invoice")
            # invoice_address = partner.child_ids.filtered(lambda r: r.type == "invoice")

            # if invoice_address:
            # record = invoice_address[0]

            billing_address = {
                "BuildingNumber": "",
                "StreetName": record.street if record.street else "Desconhecido",
                "AddressDetail": record.contact_address[0:249],
                "City": record.city if record.city else "Desconhecido",
                "PostalCode": record.zip if record.zip else "Desconhecido",
                "Province": record.state_id.name if record.state_id else "Desconhecido",
                "Country": record.country_id.code if record.country_id else "Desconhecido"
            }

            # if delivery_address:
            #     record = delivery_address[0]

            ship_address = {
                # "BuildingNumber": "",
                "StreetName": record.street if record.street else "Desconhecido",
                "AddressDetail": record.contact_address[0:200],
                "City": record.city if record.city else "Desconhecido",
                "PostalCode": record.zip if record.zip else "Desconhecido",
                "Province": record.state_id.name if record.state_id else "Desconhecido",
                "Country": record.country_id.code if record.country_id else "Desconhecido"
            }

            if partner:
                result['Customer'].append({"CustomerID": partner.id if partner.id else partner.ref,
                                           "AccountID": partner.property_account_payable_id.code if partner.property_account_receivable_id.code else "Desconhecido",
                                           "CustomerTaxID": partner.vat if partner.vat else "999999999",
                                           "CompanyName": partner.name,
                                           "Contact": "",
                                           "BillingAddress": billing_address,
                                           "ShipToAddress": ship_address,
                                           "Telephone": str(partner.phone)[0:19] if partner.phone else "000000000",
                                           "Fax": "",
                                           "Email": partner.email if partner.email else "Desconhecido",
                                           "Website": partner.website if partner.website else "Desconhecido",
                                           "SelfBillingIndicator": "0"})

            if partner:
                result['Supplier'].append({"SupplierID": partner.id if partner.id else partner.ref,
                                           "AccountID": partner.property_account_payable_id.code,
                                           "SupplierTaxID": partner.vat if partner.vat else "999999999",
                                           "CompanyName": partner.name,
                                           "Contact": "",
                                           "BillingAddress": billing_address,
                                           "ShipFromAddress": ship_address,
                                           "Telephone": str(partner.phone)[0:19] if partner.phone else "000000000",
                                           "Fax": "",
                                           "Email": partner.email if partner.email else "Desconhecido",
                                           "Website": partner.website if partner.website else "Desconhecido",
                                           "SelfBillingIndicator": "0"})

        result = dict_clean_up("", result)

        return result

    def _create_partner_account(self, vals):
        pass
        # if not vals.get('country_id') and not self.country_id:
        #     raise ValidationError(
        #         _("No country defined! To create automatically the account for the customer/supplier you have to define the country!"
        #           " Go to the customer/supplier form and set the country"))
        # country_id = self.env["res.country"].search([("code", "=", "AO")])
        # if self.env.context.get('res_partner_search_mode') == 'customer':
        #     seq = self.env['ir.sequence'].next_by_code(f'customer_account_{self.env.company.id}')
        #     code = ''
        #     if vals.get('country_id') == self.env.company.country_id.id:
        #         code = self.env.company.partner_receivable_code_prefix + seq
        #     else:
        #         code = self.env.company.fpartner_receivable_code_prefix + seq
        #
        #     account_type = self.env['account.account.type'].search([('type', '=', 'receivable')])
        #     new_account = {
        #         'name': vals['name'],
        #         'code': code,
        #         'user_type_id': account_type.id,
        #         'reconcile': True,
        #     }
        #     new_account_id = self.env['account.account'].sudo().create(new_account)
        #     vals['property_account_receivable_id'] = new_account_id.id
        #
        # if self.env.context.get('res_partner_search_mode') == 'supplier':
        #     seq = self.env['ir.sequence'].next_by_code(f'supplier_account_{self.env.company.id}')
        #     code = ''
        #     if vals.get('country_id') == self.env.company.country_id.id:
        #         code = self.env.company.partner_payable_code_prefix + seq
        #     else:
        #         code = self.env.company.fpartner_payable_code_prefix + seq
        #
        #     account_type = self.env['account.account.type'].search([('type', '=', 'payable')])
        #     new_account = {
        #         'name': vals['name'],
        #         'code': code,
        #         'user_type_id': account_type.id,
        #         'reconcile': True,
        #     }
        #     new_account_id = self.env['account.account'].sudo().create(new_account)
        #     vals['property_account_payable_id'] = new_account_id.id
        # return vals

    # @api.model
    # def create(self, vals):
    #     if self.env.company.country_id.code == "AO" and self.env.company.create_partner_account:
    #         vals["country_id"] = self.env.company.country_id.id
    #         vals = self._create_partner_account(vals)
    #     res = super(AOResPartnerAccountChart, self).create(vals)
    #     return res

    @api.constrains('vat')
    def check_vat(self):
        for partner in self:
            if partner.vat == '999999999' or partner.vat == '9999999999':
                raise ValidationError(
                    _('It is not allowed to associate the vat with the customer, as it is not valid, VAT: %s') % partner.vat)

    # def write(self, vals):
    #
    #     if self.env.company.country_id.code == 'AO':
    #         has_supplier_account = self.env.ref('l10n_ao.account_chart_321211', False)
    #         has_customer_account = self.env.ref('l10n_ao.account_chart_311211', False)
    #
    #         for partner in self:
    #             if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_vat'):
    #                 if vals.get('name') or vals.get('vat'):
    #                     invoice_exists = self.env['account.move'].search_count(
    #                         [('state', 'in', ['posted', 'cancel']),
    #                          ("partner_id", "=", partner.id)])
    #                     if invoice_exists:
    #                         if vals.get('name') and not partner.vat:
    #                             vals.pop('name')
    #                             raise ValidationError(_(
    #                                 "The name of this entity cannot be changed, because there are associated invoices and the VAT is not defined. After defining the VAT you can change the name of the Entity"))
    #                         if vals.get('vat') and partner.vat not in ["9999999999", "999999999"]:
    #                             if partner.vat:
    #                                 vals.pop('vat')
    #                                 raise ValidationError(
    #                                     _("The NIF can´t be changed, because there are already invoices associated with it!"))
    #
    #         if self.env.company.create_partner_account:
    #             if self.env.context.get('res_partner_search_mode') == 'customer' \
    #                     and self.property_account_receivable_id and \
    #                     self.property_account_receivable_id.code == has_customer_account.code:
    #                 vals['name'] = self.name
    #                 self._create_partner_account(vals)
    #             # If customer name changes and it's receivable account is defined, change the name of the receivable account
    #             elif self.env.context.get('res_partner_search_mode') == 'customer' and \
    #                     vals.get('name', False) and self.property_account_receivable_id \
    #                     and self.property_account_receivable_id.code != has_customer_account.code:
    #                 self.property_account_receivable_id.write({'name': vals['name']})
    #
    #             if self.env.context.get('res_partner_search_mode') == 'supplier' and \
    #                     self.property_account_payable_id and \
    #                     self.property_account_payable_id.code == has_supplier_account.code:
    #                 vals['name'] = self.name
    #                 self._create_partner_account(vals)
    #             # If supplier name changes and it's payable account is defined, change the name of the payable account
    #             elif self.env.context.get('res_partner_search_mode') == 'supplier' and \
    #                     vals.get('name', False) and self.property_account_payable_id.id \
    #                     and self.property_account_payable_id.code != has_supplier_account.code:
    #                 self.property_account_payable_id.write({'name': vals['name']})
    #
    #     return super(AOResPartnerAccountChart, self).write(vals)

    #
    # @api.depends('vat')
    # def nif_validate(self):
    #     if self.vat:
    #         result = requests.get(_BASE_URI + str(self.vat))
    #         if result.status_code == 200:
    #             if dict(result.json())['data']:
    #                 self.vat_valid = True
    #                 self.write({'name': dict(result.json())['data'][0]['nomeContribuinte']})
    #                 print(dict(result.json())['data'][0]['nomeContribuinte'])
    #         else:
    #             raise ValidationError("Server returned %s: %s" % (result.status_code, result.text))

    vat_valid = fields.Boolean(_('TIN Valid'))
