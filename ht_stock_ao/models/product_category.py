from odoo import models, api, fields


class HtProductCategory(models.Model):
    _inherit = 'product.category'

    code = fields.Char('Code')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda l: l.env.company)

    property_plan_sale = fields.Selection([
        ("1", 'Finished and intermediate products'),
        ("2", 'By-products, waste, residues and refuse'),
        ("3", 'Merchandise'),
        ("4", 'Consumer packaging'),
        ("5", 'Price subsidies'),
        ("7", 'Returns'),
        ("8", 'Discounts and rebates')
    ], string="Sale Plan", default="3")

    property_service_plan_sale = fields.Selection([
        ("1", 'Main services'),
        ("2", 'Secondary services'),
        ("3", 'discounts and rebates'),
    ], string="Sale Plan", default="1")

    property_plan_purchase = fields.Selection([
        ("2", 'Merchandise'),
        ("1", 'Raw material'),
        ("75239", 'Service')
    ], string="Purchase Plan", default="2")

    property_act_plan_sale = fields.Selection([
        ("1", 'National market'),
        ("2", 'Foreign Market')
    ], string="Actuation market", default="1")

    property_act_plan_purchase = fields.Selection([
        ("1", 'National market'),
        ("2", 'Foreign Market')
    ], string="Actuation market", default="1")

    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Product storable')
    ], string='Type', default='product')

    group_categ = fields.Selection([
        ("1", 'Merchandise'),
        ("2", 'Raw material'),
        ("3", 'Service'),
    ], string="Group Category")

    @api.onchange('type')
    def onchange_type(self):
        if self.type and self.group_categ:
            if self.type == 'product':
                if self.group_categ not in ["1", "2"]:
                    self.group_categ = "1"
            else:
                self.group_categ = "3"

    @api.onchange('group_categ')
    def onchange_group_categories(self):
        if self.group_categ == "1":
            account_sale = self.env['account.account'].search([('code', '=', '7131')])
            account_purchase = self.env['account.account'].search([('code', '=', '2121')])
            account = self.env['account.account'].search([('code', '=', '2631')])

            self.property_stock_valuation_account_id = account
            self.property_stock_account_input_categ_id = account_purchase
            self.property_stock_account_output_categ_id = account_sale
            self.type = 'product'
            self.property_plan_purchase = "2"
            self.property_cost_method = 'average'
            self.property_valuation = 'real_time'

            _property_valuation = self.env.ref('stock_account.default_category_valuation')
            _property_cost_method = self.env.ref('stock_account.default_category_cost_method')

            _cost_method = self.env['ir.property'].search([('id', '=', _property_cost_method.id)])
            _valuation = self.env['ir.property'].search([('id', '=', _property_valuation.id)])

            # if _property_valuation: _property_valuation.value_text = 'real_time'
            # if _property_cost_method: _property_cost_method.value_text = 'average'
            # if not _property_valuation: self.property_valuation = 'real_time'
            # if not _property_cost_method: self.property_cost_method = 'average'

        elif self.group_categ == "2":
            account_sale = self.env['account.account'].search([('code', '=', '7111')])
            account_purchase = self.env['account.account'].search([('code', '=', '2111')])
            account = self.env['account.account'].search([('code', '=', '2211')])

            self.property_stock_valuation_account_id = account
            self.property_stock_account_input_categ_id = account_purchase
            self.property_stock_account_output_categ_id = account_sale
            self.type = 'product'
            self.property_plan_purchase = "1"
            self.property_cost_method = 'average'
            self.property_valuation = 'real_time'
            _property_valuation = self.env.ref('stock_account.default_category_valuation')
            _property_cost_method = self.env.ref('stock_account.default_category_cost_method')

            _cost_method = self.env['ir.property'].search([('id', '=', _property_cost_method.id)])
            _valuation = self.env['ir.property'].search([('id', '=', _property_valuation.id)])

            # if _property_valuation: _property_valuation.value_text = 'real_time'
            # if _property_cost_method: _property_cost_method.value_text = 'average'
            # if not _property_valuation: self.property_valuation = 'real_time'
            # if not _property_cost_method: self.property_cost_method = 'average'

        elif self.group_categ == "3":
            self.type = 'service'
            self.property_plan_purchase = "752391"
            self.property_cost_method = 'standard'
            self.property_valuation = 'manual_periodic'

            _property_valuation = self.env.ref('stock_account.default_category_valuation')
            _property_cost_method = self.env.ref('stock_account.default_category_cost_method')

            _cost_method = self.env['ir.property'].search([('id', '=', _property_cost_method.id)])
            _valuation = self.env['ir.property'].search([('id', '=', _property_valuation.id)])

            # if _property_valuation: _property_valuation.value_text = 'manual_periodic'
            # if _property_cost_method: _property_cost_method.value_text = 'standard'
            # if not _property_valuation: self.property_valuation = 'manual_periodic'
            # if not _property_cost_method: self.property_cost_method = 'standard'
