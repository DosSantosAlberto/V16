from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    # tax_withhold_journal_id = fields.Many2one('account.journal', 'Withhold Journal')
    # tax_withhold_received_account_id = fields.Many2one('account.account', 'DAR Received Account')
    # tax_withhold_sent_account_id = fields.Many2one('account.account', "DAR Sent Account")

    inss = fields.Char("INSS", size=12)
    # sale_cost_center = fields.Boolean(string="Sale Cost Center")
    invoice_cost_center = fields.Boolean(string="Invoice Cost Center")
    # stock_cost_center = fields.Boolean(string="Stock Cost Center")
    # purchase_cost_center = fields.Boolean(string="Purchase Cost Center")

    accounting_year = fields.Many2one(comodel_name='account.fiscal.year', string="Accounting Year", required=False)
    account_opening_date = fields.Date(string='Opening Date', related='accounting_year.date_from', required=True,
                                       help="That is the date of the opening entry.")

    @api.model
    def create_op_move_if_non_existant(self):
        """ Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'general' to exist (required by account.move).
        """
        self.ensure_one()
        if not self.account_opening_move_id:
            default_journal = self.env['account.journal'].search(
                [('type', '=', 'general'), ('company_id', '=', self.id)], limit=1)

            if not default_journal:
                raise UserError(
                    _("Please install a chart of accounts or create a miscellaneous journal before proceeding."))

            if not self.account_opening_date: self.account_opening_date = fields.Date.context_today(self).replace(
                month=1, day=1)
            opening_date = self.account_opening_date - timedelta(days=1)

            self.account_opening_move_id = self.env['account.move'].create({
                'ref': _('Opening Journal Entry'),
                'company_id': self.id,
                'journal_id': default_journal.id,
                'date': opening_date,
            })
