import time
from datetime import datetime, timedelta, date, time
from pytz import timezone

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class Payslipline(models.Model):
    _inherit = 'hr.payslip.line'

    # @api.one
    def compute_remuneration(self):
        res = {}
        total = 0
        for slip_line in self:
            if slip_line.total >= 0:
                slip_line.remuneration = slip_line.total
            else:
                slip_line.remuneration = 0
        return total

    # @api.one
    def compute_deduction(self):
        total = 0
        for slip_line in self:
            if slip_line.total < 0:
                slip_line.deduction = abs(slip_line.total)
            else:
                slip_line.deduction = 0
        # self.deduction = total
        return total

    remuneration = fields.Float(compute=compute_remuneration, digits=(10, 2), string='Remuneration')
    deduction = fields.Float(compute=compute_deduction, digits=(10, 2), string='Deduction')


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)

    @api.onchange('struct_id')
    def _onchange_structure(self):
        structure = self.struct_id and self.struct_id.id or None
        input_records = self.env['hr.payslip.input.type'].search([])
        aa = input_records.mapped(lambda i: i.id)
        input_list = [x.id for x in input_records if
                      (len(x.struct_ids) == 0 or structure and structure in x.struct_ids.mapped(lambda i: i.id))]
        self.input_line_ids = [(5, 0, 0)]
        for input_record in input_list:
            self.input_line_ids = [(0, 0, {'input_type_id': input_record, 'amount': 0.0})]

    # @api.model
    # def get_worked_day_lines(self, contracts, date_from, date_to):
    #     """
    #     @param contract: Browse record of contracts
    #     @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
    #     """
    #     res = []
    #     # fill only if the contract as a working schedule linked
    #     for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
    #         day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
    #         day_to = datetime.combine(fields.Date.from_string(date_to), time.max)
    #
    #         # compute leave days
    #         leaves = {}
    #         calendar = contract.resource_calendar_id
    #         tz = timezone(calendar.tz)
    #         day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to,
    #                                                                calendar=contract.resource_calendar_id)
    #         for day, hours, leave in day_leave_intervals:
    #             holiday = leave.holiday_id
    #             current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
    #                 'name': holiday.holiday_status_id.name or _('Global Leaves'),
    #                 'sequence': 5,
    #                 'code': holiday.holiday_status_id.name or 'GLOBAL',
    #                 'number_of_days': 0.0,
    #                 'number_of_hours': 0.0,
    #                 'contract_id': contract.id,
    #             })
    #             current_leave_struct['number_of_hours'] += hours
    #             work_hours = calendar.get_work_hours_count(
    #                 tz.localize(datetime.combine(day, time.min)),
    #                 tz.localize(datetime.combine(day, time.max)),
    #                 compute_leaves=False,
    #             )
    #             if work_hours:
    #                 current_leave_struct['number_of_days'] += hours / work_hours
    #
    #         # compute worked days
    #         work_data = contract.employee_id.get_work_days_data(day_from, day_to,
    #                                                             calendar=contract.resource_calendar_id)
    #         employee_period = {
    #             'name': _("Normal Working Days paid at 100%"),
    #             'sequence': 1,
    #             'code': 'WORK100',
    #             'number_of_days': work_data['days'],
    #             'number_of_hours': work_data['hours'],
    #             'contract_id': contract.id,
    #         }
    #
    #         res.append(employee_period)
    #
    #         full_period = {
    #             'name': _("Full working days of the period"),
    #             'sequence': 1,
    #             'code': 'PERIOD',
    #             'number_of_days': work_data['days'],
    #             'number_of_hours': work_data['hours'],
    #             'contract_id': contract.id,
    #         }
    #
    #         res.append(full_period)
    #
    #         res.extend(leaves.values())
    #     return res

    # @api.one
    def compute_remuneration(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code == 'BAS':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.remuneration = _sum
        return res

    # @api.one
    def compute_overtimes(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code == 'HEXTRA':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.overtimes = _sum
        return res

    # @api.one
    def compute_extra_remunerations(self):
        res = {}
        for slip in self:
            slip.extra_remunerations = slip.total_remunerations - slip.remuneration - slip.overtimes
        return res

    # @api.one
    def compute_misses(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code == 'FALTA':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.misses = _sum
        return res

    # @api.one
    def compute_remuneration_inss_base(self):
        for slip in self:
            slip.remuneration_inss_base = slip.remuneration + slip.overtimes + slip.misses

    # @api.one
    def compute_remuneration_inss_extra(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code in ('ABOINSS', 'ABOINSSIRT'):
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.remuneration_inss_extra = _sum
        return res

    # @api.one
    def compute_remuneration_inss_total(self):
        for slip in self:
            slip.remuneration_inss_total = slip.remuneration_inss_base + slip.remuneration_inss_extra

    # @api.one
    def compute_amount_inss(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code == 'INSS':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.amount_inss = _sum
        return res

    # @api.multi
    def compute_amount_irt(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code == 'IRT':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.amount_irt = _sum
        return res

    def compute_extra_deductions(self):
        for p in self:
            _sum = 0.0
            for line in p.line_ids:
                if line.category_id.code not in ('INSS', 'IRT') and line.deduction > 0:
                    _sum = _sum + line.deduction
            p.extra_deductions = -_sum

    def compute_amount_base_irt(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code in ('BAS', 'HEXTRA', 'FALTA', 'ABOIRT', 'ABOINSSIRT', 'DEDINSSIRT', 'INSS'):
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.amount_base_irt = _sum
        return res

    # @api.multi
    def compute_payslip_period(self):
        res = {}
        for slip in self:
            # date_obj = datetime.strptime(slip.date_to, '%Y-%m-%d')
            date_obj = slip.date_to
            months = {
                1: _('January'),
                2: _('February'),
                3: _('March'),
                4: _('April'),
                5: _('May'),
                6: _('June'),
                7: _('July'),
                8: _('August'),
                9: _('September'),
                10: _('October'),
                11: _('November'),
                12: _('December'),
            }
            # return months[int(date_obj.month)]
            slip.payslip_period = months[int(date_obj.month)]

    # @api.multi
    def compute_total_remunerations(self):
        res = {}
        for slip in self:
            rem_total = 0.0
            for slipline in slip.line_ids:
                if not slipline.appears_on_payslip:
                    continue
                rem_total += slipline.remuneration
            res[slip.id] = rem_total
            slip.total_remunerations = rem_total
        return res

    # @api.one
    def compute_total_deductions(self):
        res = {}
        for slip in self:
            ded_total = 0.0
            for slipline in slip.line_ids:
                if not slipline.appears_on_payslip:
                    continue
                ded_total += slipline.deduction
            res[slip.id] = ded_total
            slip.total_deductions = ded_total
        return res

    # @api.multi
    def compute_total_paid(self):
        for slip in self:
            slip.total_paid = slip.total_remunerations - slip.total_deductions

    # @api.multi
    def compute_total_paid_usd(self):
        aoa_currency = self.env.ref('base.AOA')
        usd_currency = self.env.ref('base.USD')
        for slip in self:
            slip.total_paid_usd = aoa_currency._compute(aoa_currency, usd_currency, slip.total_paid)

    # @api.one
    def compute_period_working_days(self):
        for payslip in self:
            # TODO Add code to consider public holidays
            schedule = payslip.contract_id.resource_calendar_id
            total_days = 0
            date_from = fields.Date.from_string(payslip.date_from)
            date_to = fields.Date.from_string(payslip.date_to)
            delta_days = (date_to - date_from).days
            for single_date in (date_from + timedelta(n) for n in range(delta_days + 1)):
                total_days += 1
            payslip.period_working_days = total_days

    @api.onchange('date_to')
    def on_change_date_to(self):
        for payslip in self:
            aoa_currency = self.env.ref('base.AOA').with_context(date=payslip.date_to)
            usd_currency = self.env.ref('base.USD').with_context(date=payslip.date_to)
            rate_date_at = self.env["res.company"].sudo().search([], limit=1)
            if rate_date_at:
                if rate_date_at.rate_date_at == 'current_date':
                    payslip.currency_rate = self.env['res.currency']._get_conversion_rate(usd_currency, aoa_currency,
                                                                                          payslip.company_id or self.env.user.company_id,
                                                                                          date.today())
                elif rate_date_at.rate_date_at == 'payslip_close_date':
                    payslip.currency_rate = self.env['res.currency']._get_conversion_rate(usd_currency, aoa_currency,
                                                                                          payslip.company_id or self.env.user.company_id,
                                                                                          payslip.date_to)

    @api.depends('date_to', 'company_id')
    # @api.one
    def compute_currency_rate(self):
        for payslip in self:
            aoa_currency = self.env.ref('base.AOA').with_context(date=payslip.date_to)
            usd_currency = self.env.ref('base.USD').with_context(date=payslip.date_to)
            # self.currency_rate = self.env['res.currency']._get_conversion_rate(usd_currency, aoa_currency, self.company_id or self.env.user.company_id,
            #                                                                    self.date_to)
            rate_date_at = self.env["res.company"].sudo().search([('id', '=', payslip.company_id.id)], limit=1)
            if rate_date_at:
                if rate_date_at.rate_date_at == 'current_date':
                    payslip.currency_rate = self.env['res.currency']._get_conversion_rate(usd_currency, aoa_currency,
                                                                                          payslip.company_id or self.env.user.company_id,
                                                                                          date.today())
                elif rate_date_at.rate_date_at == 'payslip_close_date':
                    payslip.currency_rate = self.env['res.currency']._get_conversion_rate(usd_currency, aoa_currency,
                                                                                          payslip.company_id or self.env.user.company_id,
                                                                                          payslip.date_to)

    # @api.one
    def compute_show_total_paid_usd(self):
        for slip in self:
            slip.show_total_paid_usd = slip.env.user.company_id.show_paid_usd

    ####Send email
    def action_send_email(self, cr=None, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        uid = self.env.user
        ids = [self.id]

        template_id = self.env.ref('l10n_ao_hr_payroll.email_template_payslip_send_email', False)
        compose_form_id = False

        ctx = dict()
        ctx.update({
            'default_model': 'hr.payslip',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id and template_id.id or False,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    remuneration = fields.Float(compute=compute_remuneration, digits=(10, 2), string='Remuneration',
                                help='This is the Wage amount')
    overtimes = fields.Float(compute=compute_overtimes, digits=(10, 2), string='Overtimes',
                             help='This is the total amount for Overtimes')
    extra_remunerations = fields.Float(compute=compute_extra_remunerations, digits=(10, 2), string='Extra Remuneration')
    misses = fields.Float(compute=compute_misses, digits=(10, 2), string='Misses',
                          help='This is the total discount for misses')
    remuneration_inss_base = fields.Float(compute=compute_remuneration_inss_base, digits=(10, 2),
                                          string='Base INSS Remuneration',
                                          help='This is the Wage plus Overtime minus Misses')
    remuneration_inss_extra = fields.Float(compute=compute_remuneration_inss_extra, digits=(10, 2),
                                           string='Extra INSS Remuneration',
                                           help='Those are other INSS collectible remunerations')
    remuneration_inss_total = fields.Float(compute=compute_remuneration_inss_total, digits=(10, 2),
                                           string='Gross Remuneration')
    amount_inss = fields.Float(compute=compute_amount_inss, digits=(10, 2), string='INSS Amount')
    amount_irt = fields.Float(compute=compute_amount_irt, digits=(10, 2), string='IRT Amount')
    extra_deductions = fields.Float(compute=compute_extra_deductions, digits=(10, 2), string='Extra Deduction')
    amount_base_irt = fields.Float(compute=compute_amount_base_irt, digits=(10, 2), string='IRT Base Amount')
    period_working_days = fields.Integer(compute=compute_period_working_days, string='Payslip Days')
    payslip_period = fields.Char(compute=compute_payslip_period, string='Payslip Period')
    total_remunerations = fields.Float(compute=compute_total_remunerations, digits=(10, 2),
                                       string='Total of Remunerations')
    total_deductions = fields.Float(compute=compute_total_deductions, digits=(10, 2), string='Total of Deductions')
    total_paid = fields.Float(compute=compute_total_paid, digits=(10, 2), string='Total Paid')
    currency_rate = fields.Float('Currency Rate', dp.get_precision('Payroll Rate'), compute=compute_currency_rate,
                                 store=True)
    total_paid_usd = fields.Float(compute=compute_total_paid_usd, digits=(10, 2), string='Total Paid (USD)')
    show_total_paid_usd = fields.Boolean(compute=compute_show_total_paid_usd, string='Show Total Paid (USD)')
    wage = fields.Monetary(related="line_ids.contract_id.wage")

    @api.onchange('employee_id')
    def on_change_employee_id(self):
        for payslip in self:
            if payslip.employee_id:
                contract_id = self.env["hr.contract"].sudo().search(
                    [('employee_id', '=', payslip.employee_id.id), ('date_start', '<=', payslip.date_to), '|',
                     ('date_end', '>=', payslip.date_from),
                     ('date_end', '=', False)], limit=1)
                if contract_id:
                    payslip.contract_id = contract_id
            else:
                payslip.contract_id = False
                payslip.struct_id = False

    @api.onchange('contract_id')
    def on_change_contract_id(self):
        for payslip in self:
            if payslip.contract_id:
                struct_id = self.env["hr.payroll.structure"].sudo().search(
                    [('type_id', '=', payslip.contract_id.structure_type_id.id)], limit=1)
                if struct_id:
                    payslip.struct_id = struct_id
            else:
                payslip.name = ""


class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    # @api.multi
    def action_send_email(self):
        for slip_run in self:
            for slip in slip_run.slip_ids:
                template = self.env.ref('l10n_ao_hr_payroll.email_template_payslipsendingtemplate0')
                self.env['mail.template'].browse(template.id).send_mail(slip.id)
                template.send_mail(slip.id)
