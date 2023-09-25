from odoo import fields, models, api
from odoo.tools.misc import formatLang
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta


class SaleSummary(models.TransientModel):
    _name = 'sale.summary.wizard'
    _description = "Sales Summary Report"

    date_from = fields.Date('Date From', default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date('Date To', default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()),
                          )
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id, string="Company")
    # account_tax_ids = fields.Many2many(comodel_name="account.tax", string="Taxes")
    filter = fields.Selection([('tax', 'Taxes - IVA')], string='Filter', default='tax')

    def get_invoice(self):
        product_list = []
        data = []
        invoices = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice']),
            ('state', 'in', ['posted']),
            ('invoice_date', '>=', self.date_from), ('invoice_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ])

        invoice_lines = invoices.mapped('invoice_line_ids')
        tax_iva = self.env['account.tax'].search([('code', '=', 'IVA'), ('type_tax_use', 'in', ['sale'])])
        for line in invoice_lines:
            _total_amount = 0.0
            _iva_total_amount = 0.0
            if line.product_id and line.product_id not in product_list:
                product_list.append(line.product_id)
                line_data = {
                    'ref': line.product_id.id,
                    'name': line.product_id.name,
                }
                for tax in tax_iva:
                    net_amount = sum([
                        l.price_subtotal - l.ht_global_discount for l in invoice_lines if
                        l.product_id == line.product_id and tax in line.tax_ids
                    ])
                    line_data['net_' + str(tax.amount)] = formatLang(self.env, net_amount)
                    line_data['format_net_' + str(tax.amount)] = net_amount
                    line_data['iva_' + str(tax.amount)] = formatLang(self.env, net_amount * (tax.amount / 100))
                    line_data['format_iva_' + str(tax.amount)] = net_amount * (tax.amount / 100)
                    _total_amount += net_amount
                    _iva_total_amount += (net_amount * (tax.amount / 100))
                line_data['total'] = formatLang(self.env, _total_amount)
                line_data['format_total'] = _total_amount
                line_data['iva_total'] = formatLang(self.env, _iva_total_amount)
                line_data['format_iva_total'] = _iva_total_amount
                data.append(line_data)
        return data

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    def print(self):
        if self.filter == 'tax':
            return self.env.ref('ht_account_ao.action_report_sale_map_tax').report_action(self)
