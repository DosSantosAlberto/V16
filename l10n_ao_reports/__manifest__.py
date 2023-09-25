{
    'name': 'Angola Accounting Reports',
    'odoo_version': '16.0',
    'version': '1.1.0',
    'category': 'Localization',
    'description': """Angola Accounting Reports""",
    'author': 'Alien Group Lda',
    'website': 'https://www.alien-group.com',
    'depends': ['base', 'account_accountant', 'account_reports', 'l10n_ao'],
    'data': [
        'views/account_financial_view.xml',
        'data/financial_report_balanco.xml',
        'data/financial_report_dr.xml',
        #'data/financial_report_fluxocaixa.xml',
        #'data/financial_report_modelo_1.xml',
        'data/change_menu_parent.xml'
    ],
    'installable': True,
    'auto_install': True,
}