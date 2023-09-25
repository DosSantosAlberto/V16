from odoo import models, fields, api, _
import xmlschema
from . import saft_file_xsd
from odoo.exceptions import ValidationError


def dict_clean_up(value, var):
    new_dict = {}
    if hasattr(var, 'items'):
        for k, v in var.copy().items():
            if v == value:
                var.pop(k, None)
            elif isinstance(v, dict):
                new_v = dict_clean_up(value, v)
                new_dict[k] = new_v
            elif isinstance(v, list):
                val_list = []
                for d in v:
                    new_v = dict_clean_up(value, d)
                    val_list.append(new_v)
                new_dict[k] = val_list
            else:
                new_dict[k] = v

    return new_dict


class L10naoSAFTFile(models.Model):
    _name = "l10nao.saft.file"
    _description = "Saft file model"

    def _compute_name(self):
        return "SAFT_AO_%s_%s_%s" % (self.fiscal_year, self.tax_account_Basis, self.create_date)

    name = fields.Char("Name", readonly=True, required=True)
    state = fields.Selection([('draft', 'Draft'), ('valid', 'Valid'), ('not_valid', 'Not Valid'), ('sented', 'Sented')],
                             "State", default="draft")
    user_id = fields.Many2one('res.users', string="User", readonly=True)
    data = fields.Binary('File', readonly=True)
    text = fields.Text(string="Text", readonly=True)
    date_start = fields.Date(string="Date Start", required=True, readonly=True)
    date_end = fields.Date(string=" Date End", required=True, readonly=True)
    company_id = fields.Many2one("res.company", required=True, string="Company", readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    audit_file_version = fields.Char(string="Audit File Version", size=10, required=True, readonly=True,
                                     help="Ficheiro de auditoria informática")
    tax_account_Basis = fields.Selection(string="Document Type",
                                         selection=[('I', 'Contablidade integrada com facturação'),
                                                    ('C', 'Contablidade'),
                                                    ('F', 'Facturação'),
                                                    # ('P', 'Facturação parcial'),
                                                    ('R', 'Recibos'),
                                                    ('S', 'Autofacturação'),
                                                    ('A', 'Aquisição de bens e serviços'),
                                                    ('Q', 'Aquisição de bens e serviços integrada com a facturação')],
                                         help="Tipos de Documentos, na exportação do SAFT", required=True,
                                         readonly=True,
                                         default="I")
    fiscal_year = fields.Integer(string="Fiscal Year", required=True, readonly=True)
    product_company_tax_id = fields.Char(string="NIF", size=20, required=True, readonly=True,
                                         help="Identidade Fiscal da Empresa Produtora do Software")
    software_validation_number = fields.Char(string="Software Number", required=True, readonly=True,
                                             help="Número de validação.Atríbuido à entidade produtora "
                                                  "do software")
    product_id = fields.Char(string="Product ID", required=True, size=255, readonly=True,
                             help="Nome da aplicação que gera o SAFT (AO).")
    Product_version = fields.Char(string="Product Version", size=30, required=True, readonly=True,
                                  help="Deve ser indicada a versão da aplicação produtora do ficheiro.")
    header_comment = fields.Char(string="Header Comment", size=255, help="Comentários Adicionais")
    warnings = fields.Char("Warnings")
    is_valid = fields.Boolean(string="Is Valid", readonly=True)

    def action_validate(self):
        if self.tax_account_Basis in ["I"]:
            i_xsd_instance = saft_file_xsd.SAFT_FILE_XSD
            i_xsd_f = xmlschema.XMLSchema(i_xsd_instance)
            if i_xsd_f.is_valid(self.text):
                self.is_valid = True
                self.state = "valid"
            else:
                self.is_valid = False
                self.state = "not_valid"
                raise ValidationError(
                    _("Cannot validate the Saft file because of this error \n %s") % i_xsd_f.validate(self.text))
        if self.tax_account_Basis in ["C"]:
            c_xsd_instance = saft_file_xsd.SAFT_FILE_XSD
            c_xsd_f = xmlschema.XMLSchema(c_xsd_instance)
            print(c_xsd_f)
            if c_xsd_f.is_valid(self.text):
                self.is_valid = True
                self.state = "valid"
            else:
                self.is_valid = False
                self.state = "not_valid"
                raise ValidationError(
                    _("you cannot validate the Saft file because of this error %s") % c_xsd_f.validate(self.text))
        if self.tax_account_Basis in ["A"]:
            a_xsd_instance = saft_file_xsd.SAFT_FILE_XSD
            a_xsd_f = xmlschema.XMLSchema(a_xsd_instance)
            print(a_xsd_f)
            if a_xsd_f.is_valid(self.text):
                self.is_valid = True
                self.state = "valid"
            else:
                self.is_valid = False
                self.state = "not_valid"
                raise ValidationError(
                    _("you cannot validate the Saft file because of this error %s") % a_xsd_f.validate(self.text))
        if self.tax_account_Basis in ["F"]:
            f_xsd_instance = saft_file_xsd.SAFT_FILE_XSD
            f_xsd = xmlschema.XMLSchema(f_xsd_instance)
            print(f_xsd)
            if f_xsd.is_valid(self.text):
                self.is_valid = True
                self.state = "valid"
            else:
                self.is_valid = False
                self.state = "not_valid"
                raise ValidationError(
                    _("you cannot validate the Saft file because of this error %s") % f_xsd.validate(self.text))

    def action_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/download/saft/%s' % (self.id),
            'target': 'new',
        }

    def action_send_agt(self):
        pass

    def action_approve(self):
        pass

    def action_send_partner(self):
        pass
