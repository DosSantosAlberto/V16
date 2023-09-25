{
    'name': 'Treasury Request',
    'summary': """HS Treasury Request""",
    'version': '15.1',
    'author': 'Compllexus Lda',
    'website': "http://www.compllexus.com",
    'company': 'Compllexus Lda',
    "category": "Finance",
    'depends': ['es_treasury', 'hr'],
    'data': [
        'data/sequence.xml',

        'security/security.xml',
        'security/ir.model.access.csv',

        'views/treasury_request_view.xml',
    ],
    'license': 'OPL-1',
    'price': 150000,
    'currency': 'AOA',
    'installable': True,
    'application': True,
}
