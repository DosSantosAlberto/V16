from odoo import models, fields, api


class AnnexesA(models.TransientModel):
    _name = 'fiscal.reports.annexe'
    _description = 'Model 1 Report Annexes A'

    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id, string="Company")
    year_start = fields.Many2one(comodel_name='account.fiscal.year', string="Old Year")
    year_end = fields.Many2one(comodel_name='account.fiscal.year',
                               related='company_id.accounting_year', string="Current Year")
