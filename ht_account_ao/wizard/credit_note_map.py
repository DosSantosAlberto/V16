from odoo import fields, models, api
from odoo.tools.misc import formatLang
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta


class CreditNoteMap(models.TransientModel):
    _name = 'credit.note.map'
    _description = "Credit Note Map"

    date_from = fields.Date('Date From', default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date('Date To', default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id, string="Company")
    customer = fields.Many2many("res.partner", "credit_note_map_customer_rel", "partner_id", string="Customer")
    vendor = fields.Many2many("res.partner", "credit_note_map_vendor_rel", "partner_id", string="Vendor")
    filter = fields.Selection([
        ('out_refund', 'Customer'),
        ('in_refund', 'Vendor'),
    ], string='Filter', default='out_refund')

    @api.onchange('filter')
    def change_filter(self):
        self.customer = False
        self.vendor = False

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    def get_credit_notes(self):
        domain = [
            ('move_type', 'in', [self.filter]),
            ('state', 'in', ['posted']),
            ('invoice_date', '>=', self.date_from), ('invoice_date', '<=', self.date_to),
            ('company_id', 'in', self.company_id.ids)
        ]
        if self.customer:
            domain.extend([('partner_id', 'in', self.customer.ids)])
        elif self.vendor:
            domain.extend([('partner_id', 'in', self.vendor.ids)])

        invoices = self.env['account.move'].search(domain)
        return invoices

    def print(self):
        return self.env.ref('ht_account_ao.action_report_credit_note_map').report_action(self)
