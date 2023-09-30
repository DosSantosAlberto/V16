# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2017 Compllexus, Lda. All Rights Reserved
# http://www.compllexus.com.
{
    'name': 'Angola - Tax Withholding',
    'version': '0.1',
    'author': 'Halow Tecnology Lda',
    'category': 'Invoice',
    'sequence': 1,
    'summary': 'Tax Withholding',
    'website': 'http://www.compllexus.com',
    'description': "Angolan Tax Withholding RF II",
    'depends': [
        'ht_account_ao',
        'ht_sale_ao',
    ],
    'data': [
        'data/res_partner.xml',

        'views/account_move_view.xml',
        'views/account_payment_view.xml',
        'views/sale_view.xml',

        # 'reports/report_payment_receipt.xml',

        'wizard/account_payment_register_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'price': 75000,
    'license': 'OPL-1',
    'currency': 'AOA',
}
