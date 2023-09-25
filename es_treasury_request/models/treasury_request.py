from odoo import fields, models, api


class TreasuryRequest(models.Model):
    _name = 'treasury.request'
    _description = 'Treasury Request'

    name = fields.Char(string="Number")
    date = fields.Date(string="Requisition Date", default=fields.Date.today)
    approve_date = fields.Date(string="Approve Date")
    submit_date = fields.Date(string="Submit Date")
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee",
                                  default=lambda l: l.get_current_employee())
    department_id = fields.Many2one(related='employee_id.department_id')
    owner = fields.Integer(default=lambda l: l.env.uid)
    user_id = fields.Many2one(comodel_name="res.users", string="User", default=lambda l: l.env.user.id)
    manager = fields.Many2one(related='employee_id.parent_id')
    user_manager = fields.Many2one(related='manager.user_id')
    lines = fields.One2many('treasury.request.line', 'treasury_request', 'Lines')
    state = fields.Selection([
        ('new', 'New'),
        ('submit', 'Submitted'),
        ('cancel', 'Canceled'),
        ('approve', 'Approved')
    ], default='new', string='status')

    @api.model
    def create(self, vals):
        result = super(TreasuryRequest, self).create(vals)
        sequence = self.env['ir.sequence'].next_by_code('treasury.request')
        result.name = sequence
        return result

    def button_submit(self):
        self.submit_date = fields.Date.today()
        self.state = 'submit'

    @api.model
    def get_current_employee(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return employee_id

    def button_financial_approve(self):
        self.approve_date = fields.Date.today()
        self.state = 'approve'

    def button_cancel(self):
        self.state = 'cancel'


class TreasuryRequestLine(models.Model):
    _name = 'treasury.request.line'
    _description = 'Treasury Request Line'

    treasury_request = fields.Many2one(comodel_name="treasury.request")
    area = fields.Char(string="Area")
    name = fields.Char(string="Product")
    qty = fields.Float(string="Qt")
    price_unit = fields.Float(string="P.Unit")
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal')

    @api.depends('price_unit', 'qty')
    def _compute_subtotal(self):
        for res in self:
            res.subtotal = res.price_unit * res.qty
