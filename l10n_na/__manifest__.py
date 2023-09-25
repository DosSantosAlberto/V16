# -*- encoding: utf-8 -*-
{
    'name': 'Namibia - Accounting',
    'version': '1.0',
    'odoo_version': '16.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """Accounting Chart for Namibia""",
    'author': 'Alien Group, Lda',
    'website': 'https://www.alien-group.com',
    'depends': ['l10n_na_base', 'account', 'base_vat'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.group.template.csv',
        #'data/account_tax_report_data.xml',
        'data/account.tax.group.csv',
        'data/account.account.template.csv',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_post_data.xml',
        'data/account_chart_template_configure_data.xml',
    ],
    'license': 'LGPL-3',
}
# Copyright (C) 2022 Alien Group (<https://www.alien-group.com>).
