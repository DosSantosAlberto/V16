# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2022 Eletic Solution, Lda. All Rights Reserved
# http://www.compllexus.com.
{
    "name": "Angola - Invoicing",
    "version": "0.1",
    "author": "Compllexus",
    "category": "Accounting/Accounting",
    "sequence": 1,
    "summary": "Invoice - Angola",
    "website": "http://www.compllexus.com",
    "description": "Angolan Invoicing and AGT Rules",
    "depends": [
        "l10n_ao",
        "account_debit_note",
        "account_accountant",
        "account_payment",
        "account_reports",
        #"ao_localization",
        "account_accountant",
        "account_asset",
    ],
    "data": [
        "security/account_security.xml",
        "security/ir.model.access.csv",
        # "data/account_sequence.xml",
        # 'data/account.iva.csv',
        "data/account.cash.flow.csv",
        "data/account.fiscal.plan.csv",
        "data/paper_data.xml",
        "views/account_config_settings.xml",
        "views/account_account_view.xml",
        "views/account_fiscal_year.xml",
        "views/account_move_view.xml",
        "views/account_payment_view.xml",
        "views/res_partner_view.xml",
        "reports/sale_map_tax_report.xml",
        "reports/captive_vat_map_report.xml",
        # "reports/credit_note_map_report.xml",
        # "reports/report_invoice.xml",
        # "reports/report_payment_receipt.xml",
        "reports/payment_by_date_report.xml",
        "reports/invoice_by_date_report.xml",
        "reports/supplier_map_report.xml",
        "reports/report.xml",
        "wizard/sale_summary_wizard.xml",
        "wizard/captive_vat_map_wizard_view.xml",
        "wizard/credit_note_map_wizard_view.xml",
        "wizard/invoice_by_date_report_wizard_view.xml",
        "wizard/clearance_wizard.xml",
        "wizard/clearance_iva_wizard.xml",
        "wizard/payment_by_date_report_wizard_view.xml",
        "wizard/supplier_map_wizard_view.xml",
    ],
    "installable": True,
    "auto_install": False,
    "price": 450000,
    "license": "OPL-1",
    "currency": "AOA",
}
