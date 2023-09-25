# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2023 Compllexus, Lda. All Rights Reserved
# http://www.compllexus.com.
{
    'name': 'SAFT - Angola',
    'version': '0.1',
    'author': 'Compllexus',
    'category': 'Localization',
    'sequence': 1,
    'summary': 'SAFT - Angola',
    'website': 'http://www.compllexus.com',
    'description': "Regras fiscais com base AGT",
    'depends': [
        'ht_account_ao',
        'ht_sale_ao',
        'ht_stock_ao',
        'ht_purchase_ao',
        'account_reports',
        'report_xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/saft_report.xml',

        'wizards/saft_ao_wizard_view.xml',

        'views/res_company_view.xml',
        'views/res_config_view.xml',
        'views/account_tax_view.xml',
        'views/saft_ao_view.xml',
        'views/saft_file_ao_view.xml',
        #'views/account_move.xml',

        'reports/report_invoice_ao.xml',
        'reports/report_sale_ao.xml',
        'reports/report_delivery_slip_ao.xml',
        'reports/report_payment_receipt_ao.xml'
    ],
    'installable': True,
    'auto_install': False,
}
