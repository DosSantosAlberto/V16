from odoo import models,fields, api


class TaxRegime(models.Model):

    _name = "account.tax.regime"
    _description = "Account Tax Regime"

    name = fields.Char(string="Name", required=True, translate=True)
