from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SAFTAccountTax(models.Model):
    _inherit = "account.tax"

    country_region = fields.Char(string="Espaço Fiscal", default="AO", )

    saft_tax_type = fields.Selection(string="TAX Type", selection=[('IVA', 'IVA'), ('IS', 'Imp do Selo'),
                                                                   ('NS', 'Não sujeição a IVA ou IS')],
                                     required=True,
                                     default="NS", )
    saft_wth_type = fields.Selection(string="Withholding Type",
                                     selection=[('IRT', 'Imposto sobre o rendimento de trabalho'),
                                                ('II', 'Imposto Industrial'),
                                                ("IS", "Imposto do Selo")],
                                     domain=[("tax_on", "=", "withholding")],
                                     required=False,
                                     default="II", )
    saft_tax_code = fields.Selection(string="Tax Code",
                                     selection=[('RED', 'Reduzida'), ('NOR', 'Normal'), ('INT', 'Intermédia'),
                                                ('ISE', 'Isenta'), ('OUT', 'Outra')], required=True,
                                     default="NOR", )

    tax_type = fields.Selection(string="TAX Type", selection=[('IVA', 'IVA'), ('IS', 'Imp do Selo'),
                                                              ('NS', 'Não sujeição a IVA ou IS')],
                                required=True,
                                default="NS", )
    tax_on = fields.Selection([('invoice', 'Invoice'), ('payment', 'Tax on Payment'),
                               ('withholding', 'Withholding Tax'), ],
                              'Tax Application', readonly=False, required=True,
                              help="Define base tax application.", default='invoice')

    tax_type_with = fields.Selection(string="Withholding Type",
                                     selection=[('IRT', 'Imposto sobre o rendimento de trabalho'),
                                                ('II', 'Imposto Industrial'),
                                                ("IS", "Imposto do Selo")],
                                     domain=[("tax_on", "=", "withholding")],
                                     required=False,
                                     default="II", )
    tax_code = fields.Selection(string="Tax Code",
                                selection=[('RED', 'Reduzida'), ('NOR', 'Normal'), ('INT', 'Intermédia'),
                                           ('ISE', 'Isenta'), ('OUT', 'Outra'), ('NS', 'Não sujeição a IVA ou IS')], required=True,
                                default="NS", )
    expiration_date = fields.Date(string="Data Expiração", )
    exemption_reason = fields.Char(string="Motivo da isenção", size=60,
                                   help="No caso de IVA isento, indique qual a norma do codigo do IVA que autribui a isenção")
