{
    'name': 'Multicaixa Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Multicaixa Implementation',
    'odoo_version': '16.0',
    'version': '1.0.0',
    'description': """Multicaixa Payment Acquirer - This will allow for client to pay using the ATM
    from Angola ATM network Multicaixa. It generates references and use realtime""",
    'author': 'Alien Group Lda',
    'website': 'https://www.alien-group.com',
    'depends': ['payment'],
    'data': [
        'views/payment_multicaixa_template.xml',
        'views/payment_provider_views.xml',
        'reports/account_multicaixa_report.xml',
        'data/multicaixa.xml',
        'data/cron.xml',
        # 'report/sale_order_report.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_multicaixa/static/src/xml/payment_post_processing.xml',
        ],
        'installable': True
    }
}
