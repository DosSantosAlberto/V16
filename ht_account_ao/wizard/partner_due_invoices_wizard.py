# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import calendar
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError


class PartnerDebtInvoicesWizard(models.TransientModel):
    _name = 'l10n_ao.partner.due.invoices.wizard'
    _description = ''

    
    def company_domain(self):
        return [('id', 'in', self.env.user.company_ids.ids)]

    companies = fields.Many2many(comodel_name='res.company', string='Companies',
                                 default=lambda self: self.env.user.company_id, domain=company_domain)
    partner = fields.Many2one(comodel_name='res.partner', string='Client')
    supplier = fields.Many2one(comodel_name='res.partner', string='Supplier')
    type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], default='customer', string='Type')

    def set_domain(self, company):
        partner =  self.env['res.partner']
        if self.type == 'customer':
            partner = self.partner
        else:
            partner = self.supplier
        domain = [('partner_id', '=', partner.id), ('company_id', '=', company.id),
                  ('date_due', '<', fields.date.today()),('state','=','open')]
        return domain

    def get_invoices(self, company):
        local_context = dict(self.env.context, force_company=self.env.user.company_id.id,
                             company_id=self.env.user.company_id.id)
        domain = self.set_domain(company)
        invoices = self.env['account.invoice'].sudo().with_context(local_context).search(domain)
        total_residual = 0.0
        amount_total = 0.0
        for invoice in invoices:
            total_residual += invoice.amount_residual if invoice.move_type in ['in_invoice',
                                                                   'out_invoice'] else invoice.amount_residual_signed
            amount_total += invoice.amount_total if invoice.move_type in ['in_invoice',
                                                                     'out_invoice'] else invoice.amount_total_signed
        return {'invoices': invoices, 'total_residual': total_residual,
                'total': amount_total}

    def print(self):
        if not self.companies:
            raise ValidationError(_('Please, insert companies'))
        return self.env.ref('l10n_ao.action_report_partner_due_invoices').report_action(self)
