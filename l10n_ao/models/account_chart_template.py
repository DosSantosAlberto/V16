from odoo import fields, models, api, _


class AOAccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'
    _description = 'Add default prefix to company'
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
    employee_inss_account_code = fields.Char(_('Employee INSS account Code'), size=64, required=False,
                                             help=_("""This will add to the account the Employee INSS Number"""))
    company_inss_account_code = fields.Char(_('Company INSS account Code'), size=64, required=False,
                                            help=_("""This will add to the account the company INSS Number"""))

    tax_withhold_journal_id = fields.Many2one('account.journal', _("Tax Withhold Journal"), required=False)

    tax_withhold_received_account_id = fields.Many2one('account.account.template', _("Withhold DAR Received Account"),
                                                       required=False)
    tax_withhold_sent_account_id = fields.Many2one('account.account.template', _("Withhold DAR Sent Account"),
                                                   required=False)
    property_account_income_credit_id = fields.Many2one('account.account.template',
                                                        _('Category of Income Credit Account'))

    property_account_expense_credit_id = fields.Many2one('account.account.template',
                                                         _('Category of Expense Credit Account'))

    tax_cash_basis_account_id = fields.Many2one('account.account.template',
                                                _('Account Id for Tax Cash Basis'))

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """
        This method is used for creating journals.

        :param chart_temp_id: Chart Template Id.
        :param acc_template_ref: Account templates reference.
        :param company_id: company_id selected from wizards.multi.charts.accounts.
        :returns: True
        """
        JournalObj = self.env['account.journal']
        for vals_journal in self._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict):
            journal = JournalObj.create(vals_journal)
            if vals_journal['type'] == 'general' and vals_journal['code'] == _('CAMB'):
                company.write({'currency_exchange_journal_id': journal.id})
            if vals_journal['type'] == 'general' and vals_journal['code'] == _('TAX'):
                company.write({'tax_cash_basis_journal_id': journal.id})
        return True

    # Override the journal creation codes for default
    
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        def _get_default_account(journal_vals, type='debit'):
            # Get the default accounts
            default_account = False
            if journal['type'] == 'sale':
                default_account = acc_template_ref.get(self.property_account_income_categ_id).id
            elif journal['type'] == 'purchase':
                default_account = acc_template_ref.get(self.property_account_expense_categ_id).id

            return default_account

        journals = [{'name': _('Customer Invoices'), 'type': 'sale', 'code': _('FT'), 'document_type': 'FT', 'favorite': True, 'sequence': 5},
                    {'name': _('Vendor Bills'), 'type': 'purchase', 'code': _('FTF'), 'document_type': 'FT', 'favorite': True, 'sequence': 6},
                    {'name': _('Miscellaneous Operations'), 'type': 'general', 'code': _('DIV'), 'favorite': False,
                     'sequence': 7},
                    {'name': _('Exchange Difference'), 'type': 'general', 'code': _('CAMB'), 'favorite': False,
                     'sequence': 9},
                    {'name': _('Tax Cash Basis'), 'type': 'general', 'code': _('TAX'), 'favorite': False,
                     'sequence': 10}
                    ]
        if journals_dict != None:
            journals.extend(journals_dict)

        self.ensure_one()
        journal_data = []
        for journal in journals:
            vals = {
                'type': journal['type'],
                'name': journal['name'],
                'code': journal['code'],
                'company_id': company.id,
                'default_account_id': _get_default_account(journal, 'credit'),
                'show_on_dashboard': journal['favorite'],
            }

            if journal['type'] in ['sale', 'purchase'] and company.country_id.code == "AO":
                journal['refund_sequence'] = True
                journal['restrict_mode_hash_table'] = True
                if journal['type'] == 'sale':
                    journal['document_type'] = "FT"
            journal_data.append(vals)
        return journal_data

class AOAccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'
    _description = 'AO Account Tax Template'

    # Override to avoid the
    def _generate_tax_override(self, company):
        """ This method generate taxes from templates.

            :param company: the company for which the taxes should be created from templates in self
            :returns: {
                'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
                'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        # default_company_id is needed in context to allow creation of default
        # repartition lines on taxes
        ChartTemplate = self.env['account.chart.template'].with_context(default_company_id=company.id)
        todo_dict = {'account.tax': {}, 'account.tax.repartition.line': {}}
        tax_template_to_tax = {}

        templates_todo = list(self)
        while templates_todo:
            templates = templates_todo
            templates_todo = []

            # create taxes in batch
            tax_template_vals = []
            for template in templates:
                if all(child.id in tax_template_to_tax for child in template.children_tax_ids):
                    vals = template._get_tax_vals(company, tax_template_to_tax)
                    tax_template_vals.append((template, vals))
                else:
                    # defer the creation of this tax to the next batch
                    templates_todo.append(template)
            taxes = ChartTemplate._create_records_with_xmlid('account.tax', tax_template_vals, company)

            # fill in tax_template_to_tax and todo_dict
            for tax, (template, vals) in zip(taxes, tax_template_vals):
                tax_template_to_tax[template.id] = tax.id
                # Since the accounts have not been created yet, we have to wait before filling these fields
                todo_dict['account.tax'][tax.id] = {
                    'cash_basis_transition_account_id': template.cash_basis_transition_account_id.id,
                }

                # We also have to delay the assignation of accounts to repartition lines
                # The below code assigns the account_id to the repartition lines according
                # to the corresponding repartition line in the template, based on the order.
                # As we just created the repartition lines, tax.invoice_repartition_line_ids is not well sorted.
                # But we can force the sort by calling sort()
                all_tax_rep_lines = tax.invoice_repartition_line_ids.sorted() + tax.refund_repartition_line_ids.sorted()
                all_template_rep_lines = template.invoice_repartition_line_ids + template.refund_repartition_line_ids
                for i in range(0, len(all_template_rep_lines)):
                    # We assume template and tax repartition lines are in the same order
                    template_account = all_template_rep_lines[i].account_id
                    if template_account:
                        todo_dict['account.tax.repartition.line'][all_tax_rep_lines[i].id] = {
                            'account_id': template_account.id,
                        }

        if any(template.tax_exigibility == 'on_payment' and not company.country_id.code == "AO" for template in self):
            # When a CoA is being installed automatically and if it is creating account tax(es) whose field `Use Cash Basis`(tax_exigibility) is set to True by default
            # (example of such CoA's are l10n_fr and l10n_mx) then in the `Accounting Settings` the option `Cash Basis` should be checked by default.
            company.tax_exigibility = True

        return {
            'tax_template_to_tax': tax_template_to_tax,
            'account_dict': todo_dict
        }
