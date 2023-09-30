# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2023 Compllexus, Lda. All Rights Reserved
# http://compllexus.compllexus.com.
{
    'name': 'Angola - Sale',
    'version': '0.1',
    'author': 'Compllexus ',
    'category': 'Sales/Sales',
    'sequence': 1,
    'summary': 'Sale Management - Angola',
    'website': 'http://compllexus.compllexus.com',
    'description': "Angolan Sale Management",
    'depends': [
        'sale',
        'sale_management',
        'ht_account_ao',
        'base'
    ],
    'data': [
        # 'data/ir_sequence_data.xml',

        'views/sale_view.xml',
        'views/res_company_view.xml',
        'views/res_config_view.xml',
        'views/res_currency_view.xml',

        # 'reports/report.xml',
        # 'reports/report_sale.xml',

        'views/menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'price': 150000,
    'license': 'OPL-1',
    'currency': 'AOA',
}
