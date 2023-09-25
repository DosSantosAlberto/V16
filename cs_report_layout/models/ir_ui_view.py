from odoo import fields, models


class View(models.Model):
    _inherit = "ir.ui.view"


    TEMPLATE_VIEWS_BLACKLIST = [
        'web.html_container',
        'web.report_layout',
        'web.external_layout',
        'web.internal_layout',
        'web.basic_layout',
        'web.minimal_layout',
        'web.external_layout_background',
        'web.external_layout_boxed',
        'web.external_layout_clean',
        'web.external_layout_standard',
        'cs_report_layout.external_layout_cbs_cs_standard_1',
        'cs_report_layout.external_layout_cbs_cs_standard_1_2',
        'cs_report_layout.external_layout_cbs_cs_standard_1_3'
    ]

    