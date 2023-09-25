from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _rec_name = 'name'



    @api.onchange('type', 'categ_id')
    def _onchange_product_type(self):
        code_sale = '61'
        code_purchase = '21'
        if self.type == 'service':
            self.sale_ok = True
            code_sale = '62' + str(self.categ_id.property_service_plan_sale) + str(self.categ_id.property_act_plan_sale)
            code_purchase = '752391' or '75219'
            account = self.env['account.account'].search([('code', '=', code_sale)])
            account_purchase = self.env['account.account'].search([('code', '=', code_purchase)])
            self.property_account_income_id = account
            self.property_account_expense_id = account_purchase
        elif self.type == 'product':
            self.sale_ok = True
            code_sale += str(self.categ_id.property_plan_sale) + str(self.categ_id.property_act_plan_sale)
            code_purchase += str(self.categ_id.property_plan_purchase) + str(self.categ_id.property_act_plan_purchase)
            account = self.env['account.account'].search([('code', '=', code_sale)])
            account_purchase = self.env['account.account'].search([('code', '=', code_purchase)])
            self.property_account_income_id = account
            self.property_account_expense_id = account_purchase
        elif self.type == 'consu':
            self.sale_ok = False
            code_sale = '752191' or '75239'
            account = self.env['account.account'].search([('code', '=', code_sale)])
            self.property_account_income_id = False
            self.property_account_expense_id = account


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_plan_sale = fields.Selection([
        (1, 'Finished and intermediate products'),
        (2, 'By-products, waste, residues and refuse'),
        (3, 'Merchandise'),
        (4, 'Consumer packaging'),
        (5, 'Price subsidies'),
        (7, 'Returns'),
        (8, 'Discounts and rebates')
    ], string="Sale Plan", default=3)

    property_service_plan_sale = fields.Selection([
        (1, 'Main services'),
        (2, 'Secondary services'),
        (3, 'discounts and rebates'),
    ], string="Sale Plan", default=1)

    property_plan_purchase = fields.Selection([
        (2, 'Merchandise'),
        (1, 'Raw material'),
        (75239, 'Service')
    ], string="Purchase Plan", default=2)

    property_act_plan_sale = fields.Selection([
        (1, 'National market'),
        (2, 'Foreign Market')
    ], string="Actuation market", default=1)

    property_act_plan_purchase = fields.Selection([
        (1, 'National market'),
        (2, 'Foreign Market')
    ], string="Actuation market", default=1)
