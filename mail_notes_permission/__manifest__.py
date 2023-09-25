# -*- coding: utf-8 -*-
{
    'name': "Message Subtype Permission",
    'summary': "Allow to define with message types can be deleted",
    'description': """
        Specify in Message subtype if the subtype can be deleted or
        editable
    """,
    'website': "https://www.alien-group.com/app/rental",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['mail'],
    'data': [
        'views/mail_message_subtypes_views.xml',
    ],
    'application': False,
    'license': 'OEEL-1',
}
