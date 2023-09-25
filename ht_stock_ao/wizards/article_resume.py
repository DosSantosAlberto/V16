from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountFinaBalance(models.TransientModel):
    _name = 'article.resume.wizard'
    _description = 'Report for arcticle extract'

    start_date = fields.Date(string="Start Date", default=fields.Date.today)

    end_date = fields.Date(string="End Date", default=fields.Date.today)

    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id, string="Company")

    product_id = fields.Many2one(string="Product", comodel_name="product.product", readonly=True, )

    @api.constrains('start_date', 'end_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(("Start date cannot be greater than end date\n"
                                   " Please check dates."))

    def print(self):
        return self.env.ref('ht_stock_ao.action_article_resume_report').report_action(self)
