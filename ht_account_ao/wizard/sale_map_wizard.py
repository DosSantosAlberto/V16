from odoo import fields, models, api, _
from odoo.tools.misc import formatLang
from odoo.exceptions import ValidationError


class SaleMap(models.TransientModel):
    _name = "sale.map.wizard"
    _description = 'Sale Map'

    products = fields.Many2many(comodel_name='product.product', string='Products')
    customers = fields.Many2many(comodel_name='res.partner', string='Customers')
    type = fields.Selection([('out_invoice', 'Sale'), ('in_invoice', 'Purchase')], string='Type')
    mode = fields.Selection([('detail', 'Detail'), ('resume', 'Resume')], string='Mode', default='detail')
    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date", default=fields.Date.today)
    filter = fields.Selection([('product', 'Product')], string='Filter', default='product')
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id,
                                 string="Company")

    @api.constrains('start_date', 'end_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("Start date cannot be greater than end date\n"
                                    " Please check dates."))

    def sale_products(self, products):
        invoices = self.env['account.invoice'].search([
            ('state', 'not in', ['draft', 'cancel']),
            ('type', '=', self.type),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date)
        ])
        print(invoices)
        invoice_lines = self.env['account.invoice.line']
        for product in products:
            for invoice in invoices:
                invoice_lines += invoice.invoice_line_ids.filtered(lambda l: l.product_id.id == product.id)
        print("LINES:::::::::::::::::", invoice_lines)
        return invoice_lines

    def sale_product_resume(self, product):
        invoices = self.env['account.invoice'].search([
            ('state', 'not in', ['draft', 'cancel']),
            ('type', '=', self.type),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date)
        ])
        invoice_lines = self.env['account.invoice.line']
        for invoice in invoices:
            invoice_lines += invoice.invoice_line_ids.filtered(lambda l: l.product_id.id == product.id)
        return invoice_lines

    @staticmethod
    def get_taxes(price, taxes):
        for tax in taxes:
            if tax.tax_on == 'invoice':
                return price * (tax.amount / 100)
            elif tax.tax_on == 'invoice' and tax.price_include:
                return price * (tax.amount / 100)
        return 0.0

    @staticmethod
    def get_tax_rf(price, taxes):
        for tax in taxes:
            if tax.tax_on == 'withholding':
                return price * (tax.amount / 100)
        return 0.0

    def sale_categories(self, y):
        pass

    def print(self):
        self.sale_products(self.products)
        return self.env.ref('l10n_ao.report_sale_map').report_action(self)
