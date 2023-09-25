# -*- coding: utf-8 -*-
{
    'name': "Signature Documents",
    'version': '1.0.0',
    'odoo_version': '16.0',
    'author': "Alien Group, Lda",
    'category': 'User',
    'sequence': 2,
    'description': """""",
    'depends': ['l10n_ao'],
    'data': [
        "views/res_users.xml",
        "views/signature_image.xml",
        "reports/res_users_sign.xml",
        "security/ir.model.access.csv",

    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}