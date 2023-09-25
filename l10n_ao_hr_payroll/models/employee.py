from odoo import fields, models, api


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Char('Employee Number', help="Insert here the Employee Number")
    social_security = fields.Char('Security Number', size=64, help="Insert here the Employee Security Number")
    fiscal_number = fields.Char('Fiscal Number', size=64, help="Insert here the Employee Fiscal Number")
    payment_method = fields.Selection([('bank', 'Bank Transfer'), ('cash', 'Cash'), ('check', 'Check')],
                                      'Payment Method', default='bank')
    admission_date = fields.Date('Admission Date',
                                 help='Set this date to the first day of work, this will be needed for partial processing of wage and allowances')
    last_work_date = fields.Date('Last Work Day',
                                 help='Set this day to the last day of work before processing his last payslip. This is needed for partial processing of wage and allowances')
    address_province = fields.Selection([('BEG', 'Bengo'),
                                         ('BEN', 'Benguela'),
                                         ('BIE', 'Bie'),
                                         ('CAB', 'Cabinda'),
                                         ('CUN', 'Cunene'),
                                         ('HUA', 'Huambo'),
                                         ('HUI', 'Huila'),
                                         ('KUA', 'Kuando-Cubango'),
                                         ('KWN', 'Kwanza-Norte'),
                                         ('KWS', 'Kwanza-Sul'),
                                         ('LDA', 'Luanda'),
                                         ('LUB', 'Lubango'),
                                         ('LDN', 'Lunda-Norte'),
                                         ('LDS', 'Lunda-Sul'),
                                         ('MAL', 'Malange'),
                                         ('MOX', 'Moxico'),
                                         ('NAM', 'Namibe'),
                                         ('ZAI', 'Zaire'), ], 'Province', help='Insert here the employee municipy')
    address_county = fields.Char('County', size=20, help="Insert here the employee municipy")
    address_address = fields.Char('Address', size=600, help="Insert here the employee address")
    personal_mobile_1 = fields.Char('Personal Mobile', size=20, help="Insert here the employee personal mobile")
    personal_mobile_2 = fields.Char('Other Personal Mobile', size=20, help="Insert another employee personal mobile")
    personal_home_landline = fields.Char('Home Landline', size=20, help="Insert here employee landline number")
    personal_email = fields.Char('Personal Email', size=100, help="Insert here the employee personal email")
    bank_bank = fields.Many2one('res.bank', string='Bank', help='Select the employee bank')
    bank_account = fields.Char('Bank Account', size=100, help="Insert here the employee bank account")
    is_foreign = fields.Boolean('Is Foreign',
                                help='If this employee is foreign, please check this box. Foreign employee are subject to different rules in payslip.')

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    employee_number = fields.Char('Employee Number', help="Insert here the Employee Number")
    social_security = fields.Char('Security Number', size=64, help="Insert here the Employee Security Number")
    fiscal_number = fields.Char('Fiscal Number', size=64, help="Insert here the Employee Fiscal Number")
    payment_method = fields.Selection([('bank', 'Bank Transfer'), ('cash', 'Cash'), ('check', 'Check')],
                                      'Payment Method', default='bank')
    admission_date = fields.Date('Admission Date',
                                 help='Set this date to the first day of work, this will be needed for partial processing of wage and allowances')
    last_work_date = fields.Date('Last Work Day',
                                 help='Set this day to the last day of work before processing his last payslip. This is needed for partial processing of wage and allowances')
    address_province = fields.Selection([('BEG', 'Bengo'),
                                         ('BEN', 'Benguela'),
                                         ('BIE', 'Bie'),
                                         ('CAB', 'Cabinda'),
                                         ('CUN', 'Cunene'),
                                         ('HUA', 'Huambo'),
                                         ('HUI', 'Huila'),
                                         ('KUA', 'Kuando-Cubango'),
                                         ('KWN', 'Kwanza-Norte'),
                                         ('KWS', 'Kwanza-Sul'),
                                         ('LDA', 'Luanda'),
                                         ('LUB', 'Lubango'),
                                         ('LDN', 'Lunda-Norte'),
                                         ('LDS', 'Lunda-Sul'),
                                         ('MAL', 'Malange'),
                                         ('MOX', 'Moxico'),
                                         ('NAM', 'Namibe'),
                                         ('ZAI', 'Zaire'), ], 'Province', help='Insert here the employee municipy')
    address_county = fields.Char('County', size=20, help="Insert here the employee municipy")
    address_address = fields.Char('Address', size=600, help="Insert here the employee address")
    personal_mobile_1 = fields.Char('Personal Mobile', size=20, help="Insert here the employee personal mobile")
    personal_mobile_2 = fields.Char('Other Personal Mobile', size=20, help="Insert another employee personal mobile")
    personal_home_landline = fields.Char('Home Landline', size=20, help="Insert here employee landline number")
    personal_email = fields.Char('Personal Email', size=100, help="Insert here the employee personal email")
    bank_bank = fields.Many2one('res.bank', string='Bank', help='Select the employee bank')
    bank_account = fields.Char('Bank Account', size=100, help="Insert here the employee bank account")
    is_foreign = fields.Boolean('Is Foreign',
                                help='If this employee is foreign, please check this box. Foreign employee are subject to different rules in payslip.')