from odoo import models, api, fields, _
from . import amount_to_text_pt
from odoo.tools.misc import formatLang


class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Payment in Angola"

    amount_text = fields.Char(string="Amount in Words", compute="_get_amount_in_words", store=True)
    receipt_no = fields.Char(string="Receipt Nª")
    is_advanced = fields.Boolean(string="Is Advanced ?")

    @api.model_create_multi
    def create(self, vals_list):
        result = super(AccountPayment, self).create(vals_list)
        sequence = self.env['ir.sequence'].next_by_code('account.payment.customer') or _('RG')
        result.receipt_no = sequence
        return result

    @api.depends('name')
    def _compute_receipt_no(self):
        if self.name:
            _no = self.name.split('/', 1)
            self.receipt_no = "%s %s" % ("RG", _no[-1])

    @api.depends('amount', 'journal_id')
    def _get_amount_in_words(self):
        for payment in self:
            currency_name = "AOA"
            if payment.amount > 0 and payment.currency_id:
                if payment.currency_id.name == "AOA":
                    currency_name = "Kwanzas"
                if payment.currency_id.name == "EUR":
                    currency_name = "Euros"
                if payment.currency_id.name == "USD":
                    currency_name = "Dolares Americanos"
                payment.amount_text = amount_to_text_pt.amount_to_text(payment.amount, currency_name)

    def amount_format(self, amount):
        return formatLang(self.env, amount)
