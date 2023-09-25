from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountFinaBalance(models.TransientModel):
    _name = 'article.extract.wizard'
    _description = 'Report for arcticle extract'

    product_ids = fields.Many2many(comodel_name='product.product', string='Products')
    start_date = fields.Date(string="Start Date", default=fields.Date.today)
    end_date = fields.Date(string="End Date", default=fields.Date.today)
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id,
                                 string="Company")
    filter = fields.Selection([('by_product', 'By Product'), ('all', 'All')])

    @api.constrains('start_date', 'end_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("Start date cannot be greater than end date\n"
                                    " Please check dates."))

    @api.onchange('filter')
    def onchange_filter(self):
        if self.filter == 'all':
            self.product_ids = self.env['product.product'].search([('type', '=', 'product')])

    def get_movement_article(self):
        if self.filter == 'by_product':
            articles = self.env['stock.move.line'].search(
                [('state', '=', 'done'), ('product_id', '=', self.product_id.id)])
            return articles
        else:
            articles = self.env['stock.move.line'].search(
                [('state', '=', 'done')])
            return articles

    def print(self):
        return self.env.ref('ht_stock_ao.action_article_extract_report').report_action(self)
