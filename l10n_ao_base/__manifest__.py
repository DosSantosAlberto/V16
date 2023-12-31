{
    'name': 'Angola Base Localization',
    'version': '16.0',
    'category': 'Localization',
    'description': """Angolan localization data like Bank,Provinces""",
    'author': 'Alien Group Lda',
    'summary': "Base Localization data for Angola",
    'website': 'http://www.alien-group.com',
    'depends': ['base', 'calendar', 'product', 'base_iban'],
    'data': [
        'data/banks.xml',
        'data/country_state.xml',
        'data/country_state_county.xml',
        'data/res_lang.xml',
        'views/banks_view.xml',
        'views/res_partner_view.xml',
        'views/calendar_event_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
