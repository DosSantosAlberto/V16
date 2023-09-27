from odoo import api, fields, models, _
from odoo.exceptions import AccessError

class MailMessageSubtype(models.Model):
    _inherit = "mail.message.subtype"

    editable = fields.Boolean("Editable")
    delete = fields.Boolean("Delete")

class MailMessage(models.Model):
    _inherit = "mail.message"

    def write(self, vals):

        if 'body' in vals:
            for message in self:
                if not message.subtype_id.editable and message.body:
                    self._invalidate_documents()
                    raise AccessError(_("Only administrators are allowed to Edit this type of message"))
        res = super(MailMessage, self).write(vals)
        return res

    # def unlink(self):
    #     if not self:
    #         return True
    #     if not self.subtype_id.delete:
    #         raise AccessError(_("Only administrators are allowed to Delete this type of message"))
    #     return super(MailMessage, self).unlink()
