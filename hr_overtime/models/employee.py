from odoo import fields, models, api


class ModelName(models.Model):
    _inherit = 'hr.employee'

    # number_of_overtime = fields.Float(string="Number of overtime")

    def has_overtime(self, start_date, end_date):
        number_or_hours = 0.0
        for res in self:
            for overtime in self.env['hr.overtime'].search([
                ('is_payroll', '!=', False),
                ('start_date', '>=', start_date), ('start_date', '<=', end_date),
                ('end_date', '>=', start_date), ('end_date', '<=', end_date),
                ('employee', '=', res.id),
                ('state', '=', 'posted')
            ]):
                number_or_hours += overtime.number_of_hours
                # overtime.is_payroll = False
        print("************HORA EXTRA *************", number_or_hours)
        return number_or_hours
