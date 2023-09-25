from odoo import fields, models, api, _


class AccountCostCenter(models.Model):
    _name = "account.cost.center"
    _description = "Cost Center"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name")
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id,
                                 string="Company")

    _sql_constraints = [
        ('cost_center_unique', 'unique(code)',
         'There is already a registration for this cost center!'),
    ]


class AccountCashFlow(models.Model):
    _name = "account.cash.flow"
    _description = "Cash Flow"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name")

    _sql_constraints = [
        ('cash_flow_unique', 'unique(code)',
         'There is already a registration for this cash flow!'),
    ]


class AccountIvaPlan(models.Model):
    _name = "account.iva"
    _description = "IVA Plan"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name")
    amount = fields.Float(string='Amount')

    _sql_constraints = [
        ('tax_iva_unique', 'unique(code)',
         'There is already a registration for this IVA!'),
    ]


class AccountFiscalPlan(models.Model):
    _name = "account.fiscal.plan"
    _description = "Fiscal Plan"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name")

    _sql_constraints = [
        ('fiscal_plan_unique', 'unique(code)',
         'There is already a registration for this fiscal plan!'),
    ]


class AccountAccount(models.Model):
    _inherit = 'account.account'

    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    cash_flow = fields.Many2one(comodel_name="account.cash.flow", string="Cash Flow")
    iva_plan = fields.Many2one(comodel_name="account.iva", string="Plan IVA")
    fiscal_plan = fields.Many2one(comodel_name="account.fiscal.plan", string="Plan Fiscal")

    has_cost_center = fields.Boolean(string="Cost Center?")
    has_cash_flow = fields.Boolean(string="Cash Flow?")
    has_iva = fields.Boolean(string="IVA?")
    has_fiscal_plan = fields.Boolean(string="Fiscal?")
