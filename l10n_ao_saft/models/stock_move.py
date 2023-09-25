from odoo import fields, models, api



class SAFTStockMove(models.Model):
    _inherit = 'stock.move'

    hash = fields.Char(string="Key", default="0")
    hash_control = fields.Char(
        string="Key Version", relate='company_id.key_version')
    system_entry_date = fields.Datetime("Signature Datetime")
    movement_type = fields.Selection(string="Movement Type", size=2,
                                     selection=[('GR', 'Guia de remessa'),
                                                ('GT', 'Guia de transporte(Incluir aqui as guias globais).'),
                                                ('GA', 'Guia de movimentação de activos fixos próprios'),
                                                ('GC', 'Guia de consignação'),
                                                ('GD', 'Guia ou nota de devolução.')],
                                     help="Tipo de documento")