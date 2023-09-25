from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class AOResCompany(models.Model):
    _inherit = "res.company"

    product_company_name = fields.Char("Product Company Name", readonly=True, default="Alien Group Lda")
    product_company_website = fields.Char("Product Company Website", readonly=True,
                                          default="http://www.alien-group.com")
    product_company_tax_id = fields.Char("Product Company Tax ID", readonly=True, default="5417034975")
    software_validation_number = fields.Char("Software Validation Number", readonly=True, default="101/AGT/2019")
    tax_regime_id = fields.Many2one("account.tax.regime", "Tax Regime")
    product_id = fields.Char("Product ID", readonly=True, default="Odoo Angola Official Localization/ALIEN GROUP,LDA")
    product_version = fields.Char("Product Version", readonly=True, default="14.0.0.0")
    audit_file_version = fields.Char("Audit File Version", readonly=True, default="1.01_01")
    inss = fields.Char("INSS", size=12)

    create_partner_account = fields.Boolean(_("Create Chart Account for Partners"), required=False, readonly=False,
                                            help=_(
                                                """This will create a Chart of account for client if client bit is marked and/or for supplier"""))

    partner_receivable_code_prefix = fields.Char(_('Partner receivable Account Code Prefix'), size=64, required=False,
                                                 help=_(
                                                     """This prefix will allow to automatically create the client chart account"""))
    partner_payable_code_prefix = fields.Char(_('Partner payable Account Code Prefix'), size=64, required=False,
                                              help=_(
                                                  """This prefix will allow to automatically create the supplier chart account"""))

    fpartner_receivable_code_prefix = fields.Char(_('Foreign Partner receivable Account Code Prefix'), size=64,
                                                  required=False,
                                                  help=_(
                                                      """This prefix will allow to automatically create the client chart account"""))
    fpartner_payable_code_prefix = fields.Char(_('Foreign Partner payable Account Code Prefix'), size=64,
                                               required=False,
                                               help=_(
                                                   """This prefix will allow to automatically create the supplier chart account"""))

    employee_payslip_code_prefix = fields.Char(_('Employee Payslip Account Code Prefix'), size=64, required=False,
                                               help=_(
                                                   """This prefix will allow to automatically create the Employee PaySlip chart account"""))

    employee_advance_code_prefix = fields.Char(_('Employee Payslip Advance Account Code Prefix'), size=64,
                                               required=False,
                                               help=_(
                                                   """This prefix will allow to automatically create the Employee Advance chart account"""))
    company_inss_account_code = fields.Char(_('Company INSS account Code'), size=64, required=False,
                                            help=_("""This will add to the account the company INSS Number"""))

    invoice_printing = fields.Selection([('2', "Print Duplicate"), ('3', 'Print Triplicated')], default="2")
    have_invoices = fields.Boolean("Invoices", default=False)

    @api.onchange('inss')
    def onchange_inss(self):
        # TODO: escrever na conta do inss
        if self.env.user.company_id.company_inss_account_code:
            inss_account = self.env.user.company_id.company_inss_account_code
            account = self.env['account.account'].search([('code', '=', inss_account)])
            if account:
                account.name = self.env.user.company_id.name + '- ' + self.env.user.company_id.inss

    @api.model
    def create(self, vals):
        if vals.get("country_id") == self.env.ref("base.ao").id:
            vals["tax_regime_id"] = self.env.ref("l10n_ao.account_regime_general").id
        return super(AOResCompany, self).create(vals)

    @api.onchange('tax_regime_id')
    def onchange_regime(self):
        taxes_2_activate = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), '|', '&',
                                                           ('tax_regime_ids', 'in', [self.tax_regime_id.id]),
                                                           ('active', '=', False), ('tax_regime_ids', '=', False)])
        taxes_2_deactivate = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), '|', '&',
                                                             ('tax_regime_ids', 'not in', [self.tax_regime_id.id]),
                                                             ('active', '=', True), ('tax_regime_ids', '!=', False)])
        taxes_2_deactivate = taxes_2_deactivate - taxes_2_activate
        taxes_2_activate.write({'active': True})
        taxes_2_deactivate.write({'active': False})

    def write(self, values):
        if values.get("chart_template_id") == self.env.ref('l10n_ao.ao_chart_template').id:
            if self.env.company.country_id.code == "AO" and self.env.company.id > 1:
                self.env.company._create_partner_sequences()
                values["partner_receivable_code_prefix"] = "31121"
                values["partner_payable_code_prefix"] = "32121"
                values["fpartner_receivable_code_prefix"] = "31122"
                values["fpartner_payable_code_prefix"] = "32122"

        return super(AOResCompany, self).write(values)

    def _create_partner_sequences(self):
        """This function creates a no_gap sequence on each companies in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry.
        """
        for company in self:
            exists = self.env['ir.sequence'].search([("code", '=', f'customer_account_{company.id}')])
            if not exists:
                vals = {
                    'name': f"{company.name} Customer sequence",
                    'code': f'customer_account_{company.id}',
                    'implementation': 'no_gap',
                    'prefix': '',
                    'suffix': '',
                    'padding': 4,
                    'use_date_range': False,
                    'company_id': company.id
                }
                seq = self.env['ir.sequence'].create(vals)
            exists = self.env['ir.sequence'].search([("code", '=', f'supplier_account_{company.id}')])
            if not exists:
                vals = {
                    'name': f"{company.name} Supplier sequence",
                    'code': f'supplier_account_{company.id}',
                    'implementation': 'no_gap',
                    'prefix': '',
                    'suffix': '',
                    'padding': 4,
                    'use_date_range': False,
                    'company_id': company.id
                }
                seq = self.env['ir.sequence'].create(vals)

    def _create_payment_receipt_sequence(self):
        """This function creates a no_gap sequence on each companies in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry.
        """

        if self.chart_template_id == self.env.ref('l10n_ao.ao_chart_template'):

            vals_write = {}
            seq_account_payment = self.env['ir.sequence'].search([("code", '=', 'account.payment'),
                                                                  ("company_id", "=", {self.id})])
            if not seq_account_payment:
                vals = {
                    'name': 'Pagamentos de Clientes',
                    'code': 'account.payment',
                    'implementation': 'no_gap',
                    'prefix': 'RC %(range_y)s/',
                    'suffix': '',
                    'padding': 0,
                    'use_date_range': True,
                    'company_id': self.id}
                seq = self.env['ir.sequence'].create(vals)

            seq_account_payment = self.env['ir.sequence'].search([("code", '=', 'account.payment.sup'),
                                                                  ("company_id", "=", {self.id})])
            if not seq_account_payment:
                vals = {
                    'name': 'Pagamento de Factura de Fornecedor',
                    'code': 'account.payment.sup',
                    'implementation': 'no_gap',
                    'prefix': 'PFF %(range_y)s',
                    'suffix': '',
                    'padding': 0,
                    'use_date_range': True,
                    'company_id': self.id}
                seq = self.env['ir.sequence'].create(vals)

    @api.onchange('vat', 'country_id')
    def check_different_vat_country(self):
        if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_vat') and self.have_invoices == True:
            raise ValidationError(_("Os campos NIF e País não podem ser alterados pois ja existem facturas emitidas no "
                                    "sistema com os mesmos dados, e a AGT proíbe que se alterem tais dados da empresa após terem sido emitidas facturas"))
    # invs = self.env["account.move"].search([('company_id','=',self.ids),('company_id.country_id.code','=','AO')])
    # if invs:
    #     raise ValidationError(_("Os campos NIF e País não podem ser alterados pois ja existem facturas emitidas no "
    #                             "sistema com os mesmos dados, e a AGT proíbe que se alterem tais dados da empresa após terem sido emitidas facturas"))
