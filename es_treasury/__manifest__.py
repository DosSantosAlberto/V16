# -*- coding: utf-8 -*-
{
    'name': 'Treasury Management',
    'version': '15.0',
    'summary': 'Treasury for account organization',
    'description': 'Treasury for account organization',
    'category': 'Accounting',
    'author': 'Eletic Solution',
    'website': 'http://eletic-solution.com',
    'depends': ['account', 'hr','ht_account_ao'],
    #foi tirada a depedencia do ht_account_ao
    'data': [
        'data/sequence.xml',
        'data/rubric.xml',

        'security/security.xml',
        'security/ir.model.access.csv',

        'menu/menu.xml',
        'views/account_journal_dashboard_view.xml',
        'views/treasury_box_view.xml',
        'views/treasury_box_session_view.xml',
        'views/treasury_payment_view.xml',
        'views/es_entity_view.xml',
        'views/res_config_settings_views.xml',
        'views/treasury_cash_flow_view.xml',
        'views/treasury_bank_and_cash_view.xml',
        'views/treasury_rubric.xml',

        'reports/close_box_report.xml',
        # 'reports/box_movement_report.xml',
        'reports/box_cash_flow_report.xml',

        # 'wizard/box_movement_wizard_view.xml',
        'wizard/treasury_cash_flow_wizard_view.xml',

    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'price': 400000,
    'license': 'OPL-1',
    'currency': 'AOA',
}
