# -*- coding: utf-8 -*-
from odoo import models, api, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company = super(ResCompany, self).create(vals)
            if company.country_code == 'AO':
                company._create_secure_sequence()
        return company

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        for company in self:
            if company.country_code == 'AO':
                company._create_secure_sequence()

        return res

    def _create_secure_sequence(self):
        """This function creates a no_gap sequence on each companies in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry.
        """
        for company in self:
            if company.country_code == 'AO' and company.id != 1:
                seq = self.env['ir.sequence']
                seq_data = {
                    'implementation': 'no_gap',
                    'prefix': '%(range_year)s/',
                    'suffix': '',
                    'padding': 0,
                    'use_date_range': True,
                    'company_id': company.id}
                # CREATE QUOTATION SEQUENCE
                if not seq.search([('company_id', '=', company.id), ('code', '=', 'OU')]):
                    seq_data['name'] = 'Quotation'
                    seq_data['code'] = 'OU'
                    seq_ou = seq.create(seq_data)
                # CREATE PROPOSAL SEQUENCE
                if not seq.search([('company_id', '=', company.id), ('code', '=', 'OR')]):
                    seq_data['name'] = 'Proposal'
                    seq_data['code'] = 'OR'
                    seq_or = seq.create(seq_data)
                # CREATE PRO FORMA SEQUENCE
                if not seq.search([('company_id', '=', company.id), ('code', '=', 'PP')]):
                    seq_data['name'] = 'Pro Forma'
                    seq_data['code'] = 'PP'
                    seq_pp = seq.create(seq_data)
            elif company.country_code == 'AO' and company.id == 1:
                seq_ou = self.env.ref('l10n_ao_sale.l10n_ao_sale_qt')
                if not seq_ou.company_id:
                    seq_ou.write({'company_id': company.id})
                seq_or = self.env.ref('l10n_ao_sale.l10n_ao_sale_or')
                if not seq_or.company_id:
                    seq_or.write({'company_id': company.id})
                seq_pp = self.env.ref('l10n_ao_sale.l10n_ao_sale_pp')
                if not seq_pp.company_id:
                    seq_pp.write({'company_id': company.id})
        return {}
