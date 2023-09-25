from odoo import models, fields, api


class ContractPayroll(models.Model):
    _inherit = 'hr.contract'

    def compute_week_hours(self):
        res = {}
        for contract in self:
            _total_hours = 40
            if contract.resource_calendar_id and contract.resource_calendar_id.week_hours_final > 0:
                _total_hours = contract.resource_calendar_id.week_hours_final
            contract.week_hours = _total_hours
        return res

    # This function defines the computed wage, this can come from the employee contract or from other source like job occupied
    def compute_wage_final(self):
        res = {}
        for contract in self:
            contract.wage_final = contract.wage
        return {}

    def compute_wage_hour(self):
        res = {}
        for contract in self:
            week_hours = contract.week_hours
            contract.wage_hour = round((contract.wage_final * 12) / (week_hours * 52), 2)
        return {}

    wage_final = fields.Float(compute=compute_wage_final, digits=(10, 2), string='Computed Wage',
                              help="This is the real wage for this employee. You can define wage in contract or in job (for all employees), if you define wage in contract and job, the wage in contract will be considered.")
    wage_hour = fields.Float(compute=compute_wage_hour, string='Hour Wage',
                             help="This is the hour wage for this employee. This is computed from the working schedule using (wage * 12)/(week_hours * 52)")
    week_hours = fields.Float(compute=compute_week_hours, string='Week Hours',
                              help="This is the amount of week hours defined in working schedule for this contract.")
    remuneration_ids = fields.One2many('hr.remuneration', 'contract_id', string='Remunerations for this Contract')
