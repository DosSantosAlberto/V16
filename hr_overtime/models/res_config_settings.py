# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rate_overtime_normal = fields.Float(related='company_id.rate_overtime_normal')
    rate_overtime_exceed = fields.Float(related='company_id.rate_overtime_exceed')
    day_overtime = fields.Float(related='company_id.day_overtime')
    month_overtime = fields.Float(related='company_id.month_overtime')
    year_overtime = fields.Float(related='company_id.year_overtime')
