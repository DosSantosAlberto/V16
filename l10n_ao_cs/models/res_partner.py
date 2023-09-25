from contextlib import redirect_stderr

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer = fields.Boolean(string="Is Customer")
    supplier = fields.Boolean(string="Is Vendor")

    @api.model
    def create(self, values):
        result = super(ResPartner, self).create(values)
        print("Estou fora do if")
        if self.env.user.company_id.create_partner_account:
            print("Estou dentro do if")
            self._automatic_partner_account(result)
        return result

    def write(self, values):
        customer = values.get('customer')
        supplier = values.get('supplier')
        result = super(ResPartner, self).write(values)
        for res in self:
            if customer is not None:
                res.customer_rank = 1 if customer else 0
                res._automatic_partner_account(res)
            if supplier is not None:
                res.supplier_rank = 1 if supplier else 0
                res._automatic_partner_account(res)
        return result

    def _automatic_partner_account(self, partner):
        code = ""
        country_ao = self.env['res.country'].sudo().search([('code', '=', 'AO')])
        if partner.customer_rank > 0 or self._context.get('search_default_customer', False):
            print(100 * '-', partner.name, partner.customer, 100 * '-')
            partner_account = self.env['account.account'].search(
                [('code', '=', '31121'), ('company_id', '=', self.env.user.company_id.id)])
            if partner.property_account_receivable_id.code in [partner_account.code]:
                print(100 * '-', partner.property_account_receivable_id.code, partner_account.code, 100 * '-')
                seq = self.env['ir.sequence'].next_by_code('client.account')
                if partner.country_id == country_ao:
                    code = '%s%s' % (self.env.user.company_id.partner_receivable_code_prefix, seq)
                else:
                    code = '%s%s' % (self.env.user.company_id.fpartner_receivable_code_prefix, seq)
                # if not len(self.env['res.company'].search([])) > 1:
                # account_type = self.env['account.account'].sudo().search([('account_type', '=', 'asset_receivable')])
                account = self.env['account.account'].sudo().create({
                    'name': partner.name,
                    'code': code,
                    'account_type': 'asset_receivable',
                    'reconcile': True,
                })
                customer_account = self.env['account.account'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('name', '=', partner.name),
                     ('code', '=ilike', self.env.user.company_id.partner_receivable_code_prefix + '%')],
                    order='id desc',
                    limit=1)
                if account:
                    partner.property_account_receivable_id = account.id
                else:
                    partner.property_account_receivable_id = customer_account.id

        elif partner.supplier_rank > 0 or self._context.get('default_supplier', False):
            partner_account = self.env['account.account'].search(
                [('code', '=', '32121'), ('company_id', '=', self.env.user.company_id.id)])
            if partner.property_account_payable_id.code in [partner_account.code]:
                seq = self.env['ir.sequence'].next_by_code('supplier.account')
                if partner.country_id == country_ao:
                    code = '%s%s' % (self.env.user.company_id.partner_payable_code_prefix, seq)
                else:
                    code = '%s%s' % (self.env.user.company_id.fpartner_payable_code_prefix, seq)

                # if not len(self.env['res.company'].search([])) > 1:
                # account_type = self.env['account.account'].sudo().search([('account_type', '=', 'liability_payable')])
                account = self.env['account.account'].sudo().create({
                    'name': partner.name,
                    'code': code,
                    'account_type': 'liability_payable',
                    'reconcile': True,
                })

                customer_account = self.env['account.account'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('name', '=', partner.name),
                     ('code', '=ilike', self.env.user.company_id.partner_payable_code_prefix + '%')], order='id desc',
                    limit=1)
                if account:
                    partner.property_account_payable_id = account.id
                else:
                    partner.property_account_payable_id = customer_account.id
