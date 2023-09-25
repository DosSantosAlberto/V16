# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import calendar
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError


class InvoiceByDateWizard(models.TransientModel):
    _name = 'invoice.by.date.wizard'
    _description = ''

    def company_domain(self):
        return [('id', 'in', self.env.user.company_ids.ids)]

    start_date = fields.Date('Start date', default=date.today())
    end_date = fields.Date('End date', default=date.today())
    type = fields.Selection([('customer', 'Cliente'), ('supplier', 'Fornecedor')], default='customer', string='Type')
    state = fields.Selection([
        ('all', 'Todos'),
        ('draft', 'Rascunho'),
        ('not_paid', 'Aberto'),
        ('paid', 'Pago'),
        ('cancel', 'Cancelado'),
        ('reversed', 'Reverso'),
    ], string='Status', default='all')
    companies = fields.Many2many(comodel_name='res.company', string='Companies',
                                 default=lambda self: self.env.user.company_id, domain=company_domain)
    clients = fields.Many2many(comodel_name='res.partner', relation='invoice_by_date_clients_rel')
    suppliers = fields.Many2many(comodel_name='res.partner', relation='invoice_by_date_supplier_rel')

    def set_domain(self, company):
        if self.state != 'all':
            domain = [('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date),
                      ('state', '=', self.state), ('company_id', '=', company.id)]

            if self.state == 'paid':
                domain = [('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date),
                          ('payment_state', 'in', ['paid', 'reversed']), ('company_id', '=', company.id)]

                if self.state == 'not_paid':
                    domain = [('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date),
                              ('payment_state', '=', self.state), ('company_id', '=', company.id)]

                    if self.state == 'draft':
                        domain = [('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date),
                                  ('state', '=', self.state), ('company_id', '=', company.id)]

                        if self.state == 'cancel':
                            domain = [('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date),
                                      ('state', '=', self.state), ('company_id', '=', company.id)]
        else:
            domain = [('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date),
                      ('company_id', '=', company.id)]
        if self.type == 'customer':
            domain.append(('move_type', 'in', ['out_invoice', 'out_refund']))
            if self.clients:
                domain.append(('partner_id', 'in', self.clients.ids))
        elif self.type == 'supplier':
            domain.append(('move_type', 'in', ['in_invoice', 'in_refund']))
            if self.suppliers:
                domain.append(('partner_id', 'in', self.suppliers.ids))
        return domain

    @api.onchange('type')
    def change_type(self):
        self.clients = None
        self.suppliers = None

    def get_invoices(self, company):
        local_context = dict(self.env.context, company_id=self.env.user.company_id.id)
        domain = self.set_domain(company)
        invoices = self.env['account.move'].sudo().with_context(local_context).search(domain, order='invoice_date asc')
        total_residual = 0.0
        amount_total = 0.0
        # amount = 0.0
        for invoice in invoices:
            total_residual += invoice.amount_residual if invoice.move_type in ['in_invoice',
                                                                               'out_invoice'] else invoice.amount_residual_signed
            amount_total += invoice.amount_total if invoice.move_type in ['in_invoice',
                                                                          'out_invoice'] else invoice.amount_total_signed
            # amount_total = invoice.amount_total if invoice.move_type in ['in_invoice','out_invoice'] else invoice.amount_untaxed
        return {'invoices': invoices, 'total_residual': total_residual,
                'total': amount_total}

    def print(self):
        if not self.companies:
            raise ValidationError(_('Please, insert companies'))
        return self.env.ref('ht_account_ao.action_report_invoice_by_date_pdf').report_action(self)

    def show(self):
        if not self.companies:
            raise ValidationError(_('Please, insert companies'))
        return self.env.ref('ht_account_ao.action_report_invoice_by_date_html').report_action(self)

