# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2023 Compllexus, Lda. All Rights Reserved
# http://compllexus.compllexus.com.
{
    "name": "Angola - Accounting",
    "version": "0.1",
    "author": "Compllexus",
    "category": "Accounting/Localizations",
    "sequence": 1,
    "summary": "PGC - Angola",
    "website": "http://www.compllexus.com",
    "description": "Planos de contas para Angola",
    "depends": [
        "base",
        "account",
        "base_vat",
        "account_accountant",
    ],
    "data": [
        "security/ir.model.access.csv",
        # "data/l10n_ao_chart_data.xml",
        # "data/account_chart_template_data.xml",
        # "data/account_tax_group_data.xml",
        "data/account_note_data.xml",
        "data/account_sequence.xml",
        # "data/account_tax_data.xml",
        # "data/account_exemption_taxes.xml",
        # "data/account_chart_template_configure_data.xml",
        # "views/account_config_settings.xml",
        "views/res_partner_view.xml",
        "views/account_note_view.xml",
        "views/account_account_view.xml",
        "views/account_tax_view.xml",
    ],
    "installable": True,
    "auto_install": False,
}
