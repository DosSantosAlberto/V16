# -*- coding: utf-8 -*-
# Copyright 2019 Coop IT Easy SCRL fs
#   Compllexus <Inocencio@compllexus.com>
# License AGPL-3.0 or later (https://www.compllexus.com).


{
    'name': 'HR Loan Management',
    'version': '15.0.0.0.0',
    'summary': 'Manage Loan Requests',
    'description': """
        Helps you to manage Loan Requests of your company's staff.
        """,
    'category': 'Generic Modules/Human Resources',
    'author': "Cybrosys Techno Solutions,Open HRMS, Compllexus Lda",
    'company': 'Compllexus Lda',
    'maintainer': 'Compllexus Lda',
    'website': "https://www.compllexus.com",
    'depends': [
        'base', 'hr_payroll', 'hr', 'account', 'l10n_ao_hr_payroll', 'ao_hr',
    ],
    'data': [

        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_loan_seq.xml',
        'data/salary_rule_loan.xml',
        'views/hr_loan.xml',
        'views/hr_payroll.xml',
        'views/res_config_settings_views.xml',
        'views/hr_loan_salary_approves.xml',
        'wizard/loan_salary_amortization_wizard_view.xml',

        'reports/reports.xml',
        'reports/salary_loan_advance_report.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
