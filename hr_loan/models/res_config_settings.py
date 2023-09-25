# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    installment_loan_limit = fields.Integer(related="company_id.company_installment_loan_limit", readonly=False)
    loan_per_year = fields.Integer(related="company_id.loan_per_year", readonly=False)
    salary_advance_per_year = fields.Integer(related="company_id.salary_advance_per_year", readonly=False)


class ResCompany(models.Model):
    _inherit = "res.company"
    company_installment_loan_limit = fields.Integer(string='Installment Loan Limit', readonly=False, default=1)
    loan_per_year = fields.Integer(string="Loan Per Year", readonly=False, default=1)
    salary_advance_per_year = fields.Integer(string="Salary Advance Per Year", readonly=False, default=1)
