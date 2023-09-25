from odoo import api, fields, models, _


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        related='journal_id.default_account_id',
        domain=lambda self: "[('deprecated', '=', False), "
                            "('company_id', '=', company_id), "
                            "('account_type.type', 'not in', ('receivable', 'payable')), "
                            "'|', ('account_type', '=','asset_current'), ('id', '=', parent.default_account_id)]"
                            
    )
