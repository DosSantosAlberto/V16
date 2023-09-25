from odoo import fields, models, api


class Schedule(models.Model):
    _inherit = 'resource.calendar'

    # @api.one
    def compute_computed_week_hours(self):
        res = {}
        time_float = 0
        for schedule in self:
            for line in schedule.attendance_ids:
                time_float += (line.hour_to - line.hour_from)
            res[schedule.id] = time_float
        self.computed_week_hours = time_float
        return time_float

    # @api.one
    def compute_week_hours_final(self):
        res = 0
        for schedule in self:
            if schedule.define_manual_week_hours:
                res = schedule.manual_week_hours
                self.week_hours_final = schedule.manual_week_hours
            else:
                res = schedule.computed_week_hours
                self.week_hours_final = schedule.computed_week_hours
        return res

    define_manual_week_hours = fields.Boolean('Manually Define Week Hours',
                                              help='Check this box if you want to manually define the total of week hours for this schedule')
    manual_week_hours = fields.Float('Manual Week Hours', digits=(10, 2), help='Total work hours in the week')
    computed_week_hours = fields.Float(compute=compute_computed_week_hours, string='Computed Week Hours')
    week_hours_final = fields.Float(compute=compute_week_hours_final, string='Total Week Hours')
