# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    restrict_payment_without_balance = fields.Boolean(string="Restrict payment without balance", default=True)
    treasury_prefix_account_employee = fields.Char(string='Prefix Account Employee')
    treasury_prefix_account_social = fields.Char(string='Prefix Account Social')
    treasury_prefix_account_debtor = fields.Char(string='Prefix Account Debtor')
    treasury_prefix_account_creditor = fields.Char(string='Prefix Account Creditor')
    treasury_prefix_account_status = fields.Char(string='Prefix Account Status')
    treasury_cost_center = fields.Boolean(string="Treasury Cost Center")
    # transitional_code = fields.Char(string='Prefix Account Transitional Code')
    transitory_account = fields.Boolean(string='Transitory Account', default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    restrict_payment_without_balance = fields.Boolean(string="Restrict payment without balance", readonly=False,
                                                      related='company_id.restrict_payment_without_balance')
    treasury_prefix_account_employee = fields.Char(related='company_id.treasury_prefix_account_employee', readonly=False,)
    treasury_prefix_account_social = fields.Char(related='company_id.treasury_prefix_account_social', readonly=False,)
    treasury_prefix_account_debtor = fields.Char(related='company_id.treasury_prefix_account_debtor', readonly=False,)
    treasury_prefix_account_creditor = fields.Char(related='company_id.treasury_prefix_account_creditor', readonly=False,)
    treasury_prefix_account_status = fields.Char(related='company_id.treasury_prefix_account_status', readonly=False,)
    treasury_cost_center = fields.Boolean(related='company_id.treasury_cost_center', readonly=False,)
    transitory_account = fields.Boolean(related='company_id.transitory_account', readonly=False)
    # transitional_code = fields.Char(related='company_id.transitional_code')
