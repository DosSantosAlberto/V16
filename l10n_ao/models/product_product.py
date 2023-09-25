from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SAFTProductProduct(models.Model):
    _inherit = "product.product"

    unnumber = fields.Char(string="UNNumber", help="Preencher com o nª ONU para produtos perigosos")
    customs_details = fields.Char(string="Customs Details")

    def write(self, values):
        if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_product'):
            if values.get('name') or values.get('description'):
                invoices = self.env['account.move'].search([('state', 'in', ['posted'])])
                if invoices:
                    invoice_lines = invoices.mapped("invoice_line_ids")
                    invoice_lines_p = invoice_lines.filtered(lambda r: r.product_id.id == self.id)

                    if invoice_lines_p:
                        if 'name' in values:
                            raise ValidationError("Este artigo já foi faturado e não pode ser alterado o nome")
                            # FIXME: É preciso verificar o motivo desta linha de baixo
                            # values.pop('name')
                        if 'description' in values:
                            raise ValidationError("Este artigo já foi faturado, e não pode ser alterada sua descrição")
                            # FIXME: É preciso verificar o motivo desta linha de baixo
                            # values.pop('description')
                    return super(SAFTProductProduct, self).write(values)
                else:
                    return super(SAFTProductProduct, self).write(values)
            else:
                return super(SAFTProductProduct, self).write(values)
        else:
            return super(SAFTProductProduct, self).write(values)

    def get_saft_data(self):
        type = ""
        result = {'Product': []}
        for product in self:
            if product.type == "consu":
                type = "P"
            elif product.type == "service":
                type = "S"
            elif product.type == "product":
                type = "P"
            product_val = {
                'ProductType': type,
                'ProductCode': product.id,
                'ProductGroup': product.categ_id.name[0:49],
                'ProductDescription': product.name[0:199],
                'ProductNumberCode': product.default_code[0:59] if product.default_code else "Desconhecido",
            }
            if product.unnumber:
                product_val['UNNumber'] = product.unnumber
            if product.customs_details:
                product_val['CustomsDetails'] = product.customs_details
            result['Product'].append(product_val)
        return result


class SAFTProductTemplate(models.Model):
    _inherit = "product.template"

    # @api.constrains("taxes_id")
    # def check_vat(self):
    #     for p in self:
    #         if not p.taxes_id or not p.taxes_id.filtered(lambda r:r.saft_tax_type == 'IVA'):
    #             raise ValidationError(_("Porfavor Inclua imposto do tipo IVA na configuração do produto!"))
    #         if p.taxes_id.filtered(lambda r : ((r.saft_tax_type == 'IVA' and r.saft_tax_code == 'ISE') and not r.tax_exemption_reason_id)):
    #             raise ValidationError(_("Por favor adicione o motivo de isenção ao imposto do tipo IVA que está a tentar a atribuir ao producto!"))
