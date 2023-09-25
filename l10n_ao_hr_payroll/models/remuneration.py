from datetime import datetime
from odoo import models, fields, api


class RemunerationCode(models.Model):
    _name = 'hr.remuneration.code'
    _description = 'Remuneration Code'
    _order = 'name'

    name = fields.Char('Name', required=True, help='Insert here a fliendly name for the remuneration')
    code = fields.Char('Code', required=True,
                       help='Insert here a code (3 or 4 chars) for the remuneration. This code should not have white spaces.')
    type = fields.Selection([('remuneration', 'Remuneration'), ('deduction', 'Deduction')], 'Type', required=True)
    remuneration_ids = fields.One2many('hr.remuneration', 'remunerationcode_id', string='Remunerations in this code')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)


class Remuneration(models.Model):
    _name = 'hr.remuneration'
    _description = 'Remuneration'
    _order = 'rem_type'

    name = fields.Char('Description')
    date_start = fields.Date('Start Date', required=True, default=datetime.strftime(datetime.now(), '%Y-%m-01'))
    date_end = fields.Date('End Date')
    amount = fields.Float('Amount', digits=(10, 2), required='True', help='Insert here the amount for the remuneration')
    is_daily = fields.Boolean('Is Daily', help='Check this box if the value is daily')
    remunerationcode_id = fields.Many2one('hr.remuneration.code', string='Remuneration Code', required=True,
                                          help='Select the remuneration code for the remuneration')
    contract_id = fields.Many2one('hr.contract', string='Contract', required='True',
                                  help='Select the Contract remuneration', ondelete='cascade')
    # this field is to check the type of the remuneration and it is set on on_change of field 'remunerationcode_id'
    rem_type = fields.Selection([('remuneration', 'Remuneration'), ('deduction', 'Deduction')], 'Type')

    @api.onchange('remunerationcode_id')
    def onchange_remunerationcode_id(self):
        if self.remunerationcode_id:
            self.rem_type = self.remunerationcode_id.type
            self.name = self.remunerationcode_id.name

    @api.model
    def create(self, values):
        remuneration_code_id = values['remunerationcode_id']
        remuneration_code = self.env['hr.remuneration.code'].browse([remuneration_code_id])
        values['amount'] = abs(values['amount'])
        values['rem_type'] = remuneration_code.type
        return super(Remuneration, self).create(values)

    # @api.multi
    def write(self, values):
        if 'remunerationcode_id' in values:
            remuneration_code_id = values['remunerationcode_id']
            remuneration_code = self.env['hr.remuneration.code'].browse([remuneration_code_id])
            values['rem_type'] = remuneration_code.type
        if 'amount' in values:
            values['amount'] = abs(values['amount'])
        return super(Remuneration, self).write(values)
