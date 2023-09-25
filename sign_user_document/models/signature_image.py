from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class SignatureImage(models.Model):
    _name = "signature.image"

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    signature_image = fields.Binary("User Signature")

    # @api.model
    # def create(self,vals):
    #     signature = self.env['signature.image'].search([('company_id', '=', vals["company_id"])])
    #     if signature:
    #         raise ValidationError("Ja existe uma assinatura para este utilizador associada a esta empresa. Caso queira adicionar uma nova deve eliminar a existente")
    #
    #     res = super(SignatureImage, self).create(vals)
    #     return res
