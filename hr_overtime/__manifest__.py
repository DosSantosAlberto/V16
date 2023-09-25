# -*- coding: utf-8 -*-
# Copyright 2023 Coop IT Easy SCRL fs
#   compllexus,Inocencio Chipoia <https://compllexus.complexus.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


{
    'name': 'HR Overtime',
    'version': '1.0',
    'summary': 'Overtime Management',
    'description': 'Manage overtime of employees',
    'category': 'Hr',
    'author': 'Compllexus',
    'website': 'https://compllexus.compllexus.com',
    'depends': ['ao_hr', 'hr_attendance', 'l10n_ao_hr_payroll'],
    'data': [
        'views/overtime_view.xml',
        'views/res_config_view.xml',

        'data/sequence.xml',
        'data/overtime_data.xml',
        'data/salary_structure_data.xml',

        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'price': 0.0,
    'currency': 'AOA',
    'license': 'OPL-1',
}
