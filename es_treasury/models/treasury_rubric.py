from odoo import fields, models, api


class TreasuryRubric(models.Model):
    _name = 'treasury.rubric'
    _description = 'Treasury Rubric'

    name = fields.Char(string='Rubric')
    account_code = fields.Char(string='Account Code')
