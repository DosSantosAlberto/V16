from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import utils
from datetime import datetime, date




class SAFTAccountJournal(models.Model):
    """ Adição de cmapos requeridos pelo saft:
    3.4.3.7  trasaction_type - para filtrar na contabilidade os tipos de transação conforme abaixo
    4.1.4.2/8  self_billing - servirá para preencher os campos 4.1.4.2 InvoiceStatus e 4.1.4.8 SelfBillingIndicator, nos casos de auto-facturação
    4.1.2.7    InvoiceType  classificar com um de FT, ND, NC  ou VD e AA alienação Acivos ou DA - devol activos
    """
    _inherit = "account.journal"

    self_billing = fields.Boolean(string="Auto-Facturação",
                                  help='''Assinale, se este diário se destina a registar Auto-facturação.
            As facturas emitidas em substituição dos fornecedores, ao abrigo de acordos de auto-facturação,
             são assinaladas como tal no SAFT''')

    saft_invoice_type = fields.Selection([('FT', 'Factura'),
                                          ('ND', 'Nota de débito'),
                                          ('NC', 'Nota de Crédito'),
                                          ('VD', 'Venda a Dinheiro'),
                                          ('AA', 'Alienação de Activos'),
                                          ('DA', 'Devolução de Activos')], required=False,
                                         help="Category to classify document for SAFT-AO",
                                         default="FT", )

    payment_mechanism = fields.Selection(string="Payment Mechanism",
                                         selection=[('CC', 'Cartão crédito'), ('CD', 'Cartão débito'),
                                                    ('CI', 'Crédito documentário internacional'),
                                                    ('CO', 'Cheque ou cartão oferta'),
                                                    ('CS', 'Compensação de saldos em conta corrente'),
                                                    ('DE',
                                                     'Dinheiro electrónico,por exemplo residente em cartões de fidelidade ou de pontos'),
                                                    ('MB', 'Referências de pagamento para Multicaixa'),
                                                    ('NU', 'Numerário'),
                                                    ('OU', 'Outros meios aqui não assilados'),
                                                    ('PR', 'Permuta de bens'),
                                                    ('TB', 'Transferência bancária')])