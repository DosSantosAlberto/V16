{
    'name': 'HR and Treasury',
    'version': '15.0',
    'summary': 'Payroll in the treasury',
    'description': 'Manage payment of employees',
    'category': 'Hr',
    'author': 'Compllexus Lda',
    'website': 'www.compllexus.com',
    'depends': ['account',  'hr_payroll', 'es_treasury', 'hr'],
    'data': [
        'security/ir.model.access.csv',

        'views/hr_payment_view.xml',
        'views/payslip_view.xml',
        'views/account_payment.xml',

    ],
    'installable': True,
    'auto_install': False,
    'price': 500000,
    'currency': 'AOA',
    'license': 'OPL-1',
}
