from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import re

REGEX_CODE = r"[A-Za-z]"


class SaleOrderDocumentsType(models.Model):
    _name = 'sale.order.document.type'
    _description = 'This Model represent document type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', size=2, required=True)

    _sql_constraints = [('Code', 'UNIQUE(code, name)',
                         'The code and name must be unique per Documents Type.\nPlease specify another Code')]

    @api.model
    def create(self, values):
        if 'code' in values.keys():
            values['code'] = self._validation_code_regex(values)
        if 'name' in values.keys():
            self._verify_name(values)
        return super(SaleOrderDocumentsType, self).create(values)

    def unlink(self):
        for dt in self:
            # dt.sequence_id.unlink()
            return super(SaleOrderDocumentsType, self).unlink()

    def _validation_code_regex(self, values):
        document_type = self.search([('code', '=', values.get("code"))])
        if document_type:
            raise UserError(_(
                "the given doc name % s cannot be saved as it already exists. Contact the administrator") % values.get(
                "name"))

        match_num = 0
        if not values.get("code").isalpha():
            raise ValidationError(_("The code must contain only letters. Contact the administrator"))
        matches = re.finditer(REGEX_CODE, values['code'], re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            match_num = matchNum
        if match_num > 2:
            raise ValidationError(
                _("Document Type code cannot contain more than 2 characters. Contact the administrator"))
        return str(values.get("code")).upper()

    def _verify_name(self, values):
        document_type = self.search([('name', '=', values.get("name"))])
        if document_type:
            raise UserError(_(
                "the given doc name % s cannot be saved as it already exists. Contact the administrator") % values.get(
                "name"))
