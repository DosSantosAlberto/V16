# -*- coding: utf-8 -*-
{
    'name': "Kaeso",
    'odoo_version': '16.0',
    'version': '0.0.1',
    'author': "Alien Group Lda",
    'category': 'Customization',
    'description': """Support for every Kaeso Customization""",
    'depends': ['sale_renting', 'sale_temporal'],
    'data': [
        #"reports/sale_order_report.xml",
        #"security/product_category_record_rules.xml",
        #"security/security.xml",
        #"views/product_category.xml",
        #"views/account_invoice.xml",
        "views/sale_order.xml",
        #"views/fleet_vehicle_model_brand.xml",
        #"views/fleet_service_type.xml",
        "wizard/rental_configurator.xml",
        #"views/sign_views.xml",
        #"views/maintenance_equipment_views.xml",
        #"views/survey_views.xml",

    ],
    'application': False,
    'installable': True,

}
