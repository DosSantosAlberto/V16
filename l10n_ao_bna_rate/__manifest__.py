{
    'name': 'Alien Group Lda - BNA Rates',
    'odoo_version': '16.0',
    'version': '1.0.0',
    'category': 'Account',
    'sequence': 1,
    'summary': 'BNA Rates',
    'description': "BNA Rates",
    'author': 'Alien Group Lda',
    'website': 'http://www.alien-group.com',
    'depends': [
        'base',
    ],
    'data': [
        'data/cron_read_rates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
