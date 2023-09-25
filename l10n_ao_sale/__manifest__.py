# -*- coding: utf-8 -*-
{
    'name': "Angola Sales",
    'odoo_version': '16.0',
    'version': '1.0.1',
    'author': "Alien Group, Lda",
    'category': 'Sale',
    'sequence': 2,
    'description': """Support for showing withholding/retention in the sales order view and report""",
    'depends': ['l10n_ao_cs', 'sale_management'],
    'data': [
        'security/security.xml',
        "data/sale_sequence.xml",
        "data/sale_order_documents_type.xml",
        "reports/report_definition.xml",
        "reports/sale_report_agt.xml",
        "reports/invoice_agt_report_templates.xml",
        "views/res_config_settings.xml",
        'views/inherit_sale_views.xml',
        "views/sale_order_view.xml",
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
}
