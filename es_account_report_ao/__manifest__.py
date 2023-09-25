# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2022 Eletic Solution Lda, Lda. All Rights Reserved
# http://www.ticblac.com.
{
    'name': 'Angola - Accounting Reports',
    'version': '15.0',
    'author': 'Eletic Solution Lda',
    'category': 'Accounting/Accounting',
    'sequence': 1,
    'summary': 'Angolan Accounting Reports',
    'website': 'http://www.eletic-solution.com',
    'description': "Accounting Reports",
    'depends': [
        'l10n_ao',
        'ht_account_ao',
    ],
    'data': [
        'data/paper_data.xml',
        'menu/menu.xml',

        'security/ir.model.access.csv',

        'views/account_move_line_view.xml',

        'wizard/trial_balance_wizard_view.xml',
        'wizard/account_extract_wizard_view.xml',
        'wizard/agt_model_1_wizard.xml',
        'wizard/agt_model_2_wizard.xml',
        # 'wizard/agt_model_5_wizard.xml',
        'wizard/account_demonstation_wizard.xml',
        'wizard/account_balance_wizard.xml',
        'wizard/account_journal_wizard_view.xml',
        'wizard/cash_flow_wizard.xml',
        'wizard/balance_notes_wizard.xml',
        'wizard/amortization_map_wizard_view.xml',
        'reports/report.xml',
        'reports/account_report_trial_balance_ao.xml',
        'reports/account_extract_report.xml',
        'reports/account_demonstration_fun_report.xml',
        'reports/account_demonstration_nat_report.xml',
        'reports/account_balance_report.xml',
        'reports/account_journal_report.xml',
        'reports/model_1_report.xml',
        'reports/model_2_report.xml',
        # 'reports/model_5_report.xml',
        'reports/cash_flow_dir.xml',
        'reports/balance_notes_report.xml',
        'reports/demonstration_notes_report.xml',
        'reports/amortization_map_report.xml',

    ],
    'installable': True,
    'auto_install': False,
    'price': 250000,
    'license': 'OPL-1',
    'currency': 'AOA',
}
