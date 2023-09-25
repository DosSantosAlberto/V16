from odoo import models, fields, api, _

mechanisms = [('CD', 'Cartão débito'),
              ('CC', 'Cartão crédito'),
              ('MB', 'Referências de pagamento para Multicaixa'),
              ('NU', 'Numerário'),
              ('CI', 'Crédito documentário internacional'),
              ('CO', 'Cheque ou cartão oferta'),
              ('CS', 'Compensação de saldos em conta corrente'),
              ('DE', 'Dinheiro electrónico,por exemplo residente em cartões de fidelidade ou de pontos'),
              ('OU', 'Outros meios aqui não assilados'),
              ('PR', 'Permuta de bens'),
              ('TB', 'Transferência bancária')]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_mechanism = fields.Selection(string="Payment Mechanism", selection=mechanisms)

    _sql_constraints = [('unique_reference', 'UNIQUE(payment_reference)',
                         '  de referência do pagamento deve ser único!')]

    payment_state = fields.Selection(related='move_id.payment_state')
    invoice_date = fields.Date(related='move_id.invoice_date')
    sequence_saft_rf = fields.Char()
