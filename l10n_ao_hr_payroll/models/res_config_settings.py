# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo import api


class ResCompany(models.Model):
    _inherit = 'res.company'

    close_date_option = fields.Selection([('last', 'Last Day'), ('specific', 'Set Date')], 'Close Date Mode')
    close_date = fields.Integer('Close Date', default=eval('25'))
    show_paid_usd = fields.Boolean(default=False, string='Show Amount Paid in USD')
    rate_date_at = fields.Selection([('payslip_close_date', 'Payslip Close Date'),('current_date', 'Current Date')], default='current_date', string="Rate Date At")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    close_date_option = fields.Selection(related='company_id.close_date_option')
    close_date = fields.Integer(related='company_id.close_date')
    show_paid_usd = fields.Boolean(related='company_id.show_paid_usd', readonly=False)
    rate_date_at = fields.Selection([('current_date', 'Current Date'), ('payslip_close_date', 'Payslip Close Date')], related='company_id.rate_date_at', readonly=False)

