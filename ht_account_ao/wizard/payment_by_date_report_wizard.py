# -*- coding: utf-8 -*-
from odoo import models, fields, api
import calendar
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError


class PaymentByDateWizard(models.TransientModel):
    _name = 'payment.by.date.wizard'
    _description = ''

    
    def company_domain(self):
        return [('id', 'in', self.env.user.company_ids.ids)]

    
    def journal_domain(self):
        if self.journal_type == 'all':
            return [('company_id', 'in', self.companies.ids)]
        else:
            return [('company_id', 'in', self.companies.ids), ('type', '=', self.journal_type)]

    start_date = fields.Date('Start date', default=date.today())
    end_date = fields.Date('End date', default=date.today())
    payment_type = fields.Selection(
        [('inbound', 'Receive Money'), ('outbound', 'Send Money'), ('transfer', 'Internal Transfer')],
        default='inbound', string='Payment Type')
    state = fields.Selection(
        [('all', 'All'), ('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),
         ('cancelled', 'Cancelled')], readonly=False, default='all', string="Status")
    companies = fields.Many2many(comodel_name='res.company', string='Companies',
                                 default=lambda self: self.env.user.company_id, domain=company_domain)
    journals = fields.Many2many(comodel_name='account.journal', string='Journals')
    clients = fields.Many2many(comodel_name='res.partner', string='Clients',relation='payment_by_date_clients_rel')
    suppliers = fields.Many2many(comodel_name='res.partner', string='Suppliers',relation='payment_by_date_clients_rel')

    @api.onchange('payment_type')
    def change_payment_type(self):
        self.clients = None
        self.suppliers = None

    def set_domain(self, company):
        if self.state != 'all':
            domain = [('move_id.date', '>=', self.start_date), ('move_id.date', '<=', self.end_date),
                      ('state', '=', self.state), ('company_id', '=', company.id),
                      ('payment_type', '=', self.payment_type), ('journal_id', 'in', self.journals.ids)]
        else:
            domain = [('move_id.date', '>=', self.start_date), ('move_id.date', '<=', self.end_date),
                      ('company_id', '=', company.id),
                      ('payment_type', '=', self.payment_type), ('journal_id', 'in', self.journals.ids)]
        if self.payment_type == 'inbound' and self.clients:
            domain.append(('partner_id', 'in', self.clients.ids))
        if self.payment_type == 'outbound' and self.clients:
            domain.append(('partner_id', 'in', self.suppliers.ids))
        return domain

    def get_payments(self, company):
        local_context = dict(self.env.context, force_company=self.env.user.company_id.id,
                             company_id=self.env.user.company_id.id)
        domain = self.set_domain(company)
        payments = self.env['account.payment'].sudo().with_context(local_context).search(domain, order='id asc')
        return {'payments': payments, 'total': sum([payment.amount for payment in payments])}

    def print(self):
        if not self.companies:
            raise ValidationError('Please, insert companies')
        if not self.journals:
            raise ValidationError('Please, insert journals')
        return self.env.ref('ht_account_ao.action_report_payment_by_date_pdf').report_action(self)
    
    
    def show(self):
        if not self.companies:
            raise ValidationError('Please, insert companies')
        if not self.journals:
            raise ValidationError('Please, insert journals')
        return self.env.ref('ht_account_ao.action_report_payment_by_date_html').report_action(self)
