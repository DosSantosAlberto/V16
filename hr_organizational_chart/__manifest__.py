

{
    'name': 'HR Organizational Chart',
    'version': '15.0.1.0.0',
    'summary': 'HR Employees organizational chart',
    'description': 'HR Employees organizational chart',
    'author': 'Cybrosys Techno solutions,COMPLLEXUS',
    'company': 'Cybrosys Techno Solutions,COMPLLEXUS',
    'maintainer': 'Cybrosys Techno Solutions',
    'live_test_url': 'https://youtu.be/dyCzplsAysQ',
    'category': 'Generic Modules/Human Resources',
    'website': "https://www.cbs.compllexus.com",
    'depends': ['hr'],
    'data': [
        'views/show_employee_chart.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_organizational_chart/static/src/js/organizational_view.js',
            'hr_organizational_chart/static/src/scss/chart_view.scss',


        ],
        'web.assets_qweb': [
            'hr_organizational_chart/static/src/xml/chart_view.xml',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
