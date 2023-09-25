from odoo import fields, models, api


class HsLoan(models.Model):
    _name = 'hs.loan'
    _description = 'Borrowing'

    name = fields.Char(string="Name")
    type = fields.Selection([
        ('outbound', 'Send Loan'), ('inbound', 'Receive Loan')
    ], string="Loan Type")
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('status', 'Status'),
        ('gb', 'Governing Body'),
        ('employee', 'Employee'),
        ('other_dev', 'Other Debtors'),
        ('other_cred', 'Other creditors'),
    ], string="Partner Type")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ], string="State")
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee")
    date = fields.Date = fields.Date(string="Payment Date", default=fields.Date.today)
    description = fields.Text('Description')
    other_name = fields.Char(string="name")

    def post(self):
        pass

    def action_draft(self):
        pass