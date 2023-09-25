# -*- coding: utf-8 -*-
{
    'name': "Angola Purchase Localization",
    'odoo_version': '16.0',
    'version': '1.0.1',
    'author': "Alien Group Lda",
    'website': 'http://www.alien-group.com',
    'category': 'Accounting/Localizations',
    'sequence': 2,
    'description': """Angola Localization for Purchase""",
    'depends': ['l10n_ao', 'purchase'],
    'data': [
        'views/purchase_order_view.xml',
        # 'reports/purchase_order_report.xml',
        'reports/purchase_order_report_agt.xml',
        'reports/purchase_quotation_report_agt.xml',
        'reports/purchase_reports.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
}
