from datetime import datetime
from odoo import fields, models, api
from odoo.tools.misc import formatLang
import time
from dateutil.relativedelta import relativedelta



class CaptiveVatMap(models.TransientModel):
    _name = 'captive.vat.map'
    _description = "Captive Vat Map"

    date_from = fields.Date('Date From', default=time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id, string="Company")
    customer = fields.Many2many("res.partner", "captive_map_customer_rel", "partner_id", string="Customer")
    vendor = fields.Many2many("res.partner", "captive_map_vendor_rel", "partner_id", string="Vendor")
    filter = fields.Selection([
        ('out_refund', 'Customer'),
        ('in_refund', 'Vendor'),
    ], string='Filter', default='out_refund')

    @api.onchange('filter')
    def change_filter(self):
        self.customer = False
        self.vendor = False

    def get_payment_withhold(self):
        data = []
        count_line = 1
        domain = [
            ('state', 'in', ['posted']),
            ('partner_deductible_vat', '!=', 'none'),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ]
        if self.customer:
            domain.extend([('partner_id', 'in', self.customer.ids)])
        elif self.vendor:
            domain.extend([('partner_id', 'in', self.vendor.ids)])

        payments = self.env['account.payment'].search(domain)

        invoices = payments.mapped('reconciled_invoice_ids')
        for invoice in invoices:
            count_payment = 1
            line_data = {
                'n': count_line,
                'nif': invoice.partner_id.vat,
                'name': invoice.partner_id.name,
                'inv_number': invoice.name,
                'inv_date': invoice.invoice_date,
                'inv_amount': invoice.amount_untaxed,
                'inv_tax': invoice.amount_tax,
                'inv_total': invoice.amount_total
            }
            payment_lines = invoice.sudo()._get_reconciled_info_JSON_values()
            for line in payment_lines:
                payment_id = self.env['account.payment'].browse(line['account_payment_id'])
                if len(payment_id.reconciled_invoice_ids) > 1:
                    continue
                captive_50 = payment_id.deductible_vat if payment_id.partner_deductible_vat != 'state' else 0.0
                captive_100 = payment_id.deductible_vat if payment_id.partner_deductible_vat == 'state' else 0.0
                if count_payment == 1:
                    line_data['pay_number'] = payment_id.name
                    line_data['pay_date'] = payment_id.date
                    line_data['pay_amount'] = payment_id.amount
                    line_data['pay_tax'] = payment_id.deductible_vat
                    line_data['pay_total'] = payment_id.amount + payment_id.deductible_vat
                    line_data['captive_50'] = captive_50
                    line_data['captive_100'] = captive_100
                    data.append(line_data)
                    count_line += 1
                else:
                    line_data = {
                        'n': "",
                        'nif': "",
                        'name': "",
                        'inv_number': "",
                        'inv_date': "",
                        'inv_amount': "",
                        'inv_tax': "",
                        'inv_total': "",
                        'pay_number': payment_id.name,
                        'pay_date': payment_id.date,
                        'pay_amount': payment_id.amount,
                        'pay_tax': payment_id.deductible_vat,
                        'pay_total': payment_id.amount + payment_id.deductible_vat,
                        'captive_50': captive_50,
                        'captive_100': captive_100,
                    }
                    data.append(line_data)

                count_payment += 1
        return data

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    def print(self):
        return self.env.ref('ht_account_ao.action_report_captive_vat').report_action(self)
