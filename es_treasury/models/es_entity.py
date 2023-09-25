from odoo import fields, models, api, _
from odoo.exceptions import UserError


class EsEntity(models.Model):
    _name = "es.entity"
    _description = "Entity"

    photo = fields.Binary(string="Photo")
    name = fields.Char(string="Name")
    mobile = fields.Char(string="Mobile")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    bi = fields.Char(string="BI")
    vat = fields.Char(string="NIF")
    passport = fields.Char(string="Passport")
    is_foreign = fields.Boolean(" Is foreign?")
    creditor = fields.Boolean(string="Creditor")
    debtor = fields.Boolean(string="Debtor")
    is_status = fields.Boolean(string='Is Status')
    country_id = fields.Many2one(comodel_name="res.country", string="Origen Country",
                                 default=lambda l: l.env.ref('base.ao'))
    account_id = fields.Many2one(comodel_name="account.account", string="Account")

    @api.constrains('is_foreign')
    def chek_nationality(self):
        if self.is_foreign and self.country_id.code.upper() == 'AO':
            raise UserError(_("Altera o Pais para ser considerado estangeiro.\n"
                              "Ou desmarcar o campo estrangeiro para ser considerado Angolano"))

    @api.onchange('is_foreign')
    def onchange_foreign(self):
        if self.is_foreign:
            self.country_id = False
        else:
            self.country_id = self.env.ref('base.ao')
