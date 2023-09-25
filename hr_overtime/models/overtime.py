from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import datetime
from . import utils


class ModelName(models.Model):
    _name = 'hr.overtime'
    _description = 'Overtime'

    name = fields.Char(string="Nome")
    employee = fields.Many2one(comodel_name="hr.employee", string="Funcionario")
    start_date = fields.Date(string="data de Inicio", default=fields.Date.today)
    end_date = fields.Date(string="Data do Fim", default=fields.Date.today)
    start_date_time = fields.Datetime(string="data de Inicio", default=fields.Datetime.now)
    end_date_time = fields.Datetime(string="Data do Fim", default=fields.Datetime.now)
    department = fields.Many2one(comodel_name="hr.department", string="Departamento", related='employee.department_id')
    category = fields.Many2many(comodel_name="hr.employee.category", string="Categoria",
                                related='employee.category_ids')
    manager = fields.Many2one(comodel_name="hr.employee", string="Director", related='employee.parent_id')
    is_payroll = fields.Boolean(string="Incluir na folha de pagamento")
    approved_date = fields.Date(string="Data de aprovação")
    approved_by = fields.Many2one(comodel_name="res.users", string="Aprovado por")
    number_of_hours = fields.Float(string="Numeros de  Horas")
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('posted', 'Publicado'),
        ('cancelled', 'Cancelado'),
        ('paid', 'Pago'),
    ], string="Estado", default='draft')
    description = fields.Text(string="descrição")

    @api.onchange('start_date_time', 'end_date_time')
    def onchange_date(self):
        self.start_date = self.start_date_time
        self.end_date = self.end_date_time

    @api.constrains('start_date_time', 'end_date_time')
    def check_date(self):
        if self.start_date_time > self.end_date_time:
            raise ValidationError(" Data inicial superior  a data final.\n Por favor rever as datas")
        else:
            self.post()
            self.action_draft()
        if self.number_of_hours >= 9.0:
            raise ValidationError(" 8 horas Maximo ")

    @api.model
    def create(self, values):
        result = super(ModelName, self).create(values)
        sequence = self.env['ir.sequence'].next_by_code(
            'overtime.seq') or '/'
        result.name = sequence
        return result

    def post(self):
        _start_date = self.start_date_time
        _end_date = self.end_date_time
        time = (_end_date - _start_date)
        self.number_of_hours = utils.rule_overtime(time)
        self.approved_date = fields.Date.today()
        self.approved_by = self._uid
        self.state = 'posted'

    def action_draft(self):
        self.state = 'draft'
