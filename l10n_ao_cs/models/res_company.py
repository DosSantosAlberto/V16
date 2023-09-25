from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    inv_signed = fields.Boolean('Sign Invoice')
    partner_receivable_code_prefix = fields.Char('Partner receivable Account Code Prefix', size=64, default='31121')
    partner_payable_code_prefix = fields.Char('Partner payable Account Code Prefix', size=64, default='32121')
    fpartner_receivable_code_prefix = fields.Char('F. Partner receivable Account Code Prefix', size=64, default='31122')
    fpartner_payable_code_prefix = fields.Char('F. Partner payable Account Code Prefix', size=64, default='32122')
    control_account_nature = fields.Boolean(string="Control of Account Nature")
    # tax_withhold_journal_id = fields.Many2one('account.journal', 'Withhold Journal')
    # tax_withhold_received_account_id = fields.Many2one('account.account', 'DAR Received Account')
    # tax_withhold_sent_account_id = fields.Many2one('account.account', "DAR Sent Account")

    inss = fields.Char("INSS", size=12)
    # sale_cost_center = fields.Boolean(string="Sale Cost Center")
    # invoice_cost_center = fields.Boolean(string="Invoice Cost Center")
    # stock_cost_center = fields.Boolean(string="Stock Cost Center")
    # purchase_cost_center = fields.Boolean(string="Purchase Cost Center")
    automatic_partner_account = fields.Boolean(string="Create Automatic Account Partners?")

    # accounting_year = fields.Many2one(comodel_name='account.fiscal.year', string="Accounting Year")
    # account_opening_date = fields.Date(string='Opening Date', related='accounting_year.date_from',
