from odoo import api, models, fields, api, _
from odoo.exceptions import ValidationError
from . import utils
from datetime import datetime


class SAFTSaleOrder(models.Model):
    _inherit = 'sale.order'

    work_type = fields.Selection(
        [('OR', 'ORÇAMENTO'), ('PP', 'PROFORMA')], default='PP', string="Document Type")
    hash = fields.Char(string="Key", default="0")
    hash_control = fields.Char(
        string="Key Version", relate='company_id.key_version')
    system_entry_date = fields.Datetime("Signature Datetime")

    sequence_int = fields.Integer('Sequence int')

    def clean_number_sale_order(self, date_start, date_end):
        domain = [('state', 'in', ['sale', 'done']), ('move_type', 'in', ['out_invoice']),
                  ('invoice_date', '>=', date_start), ('invoice_date', '<=', date_end)]
        invoices = self.search(domain)
        for rec in invoices:
            key = 'cp.sat.sequence'
            ir_paramenter = self.env['ir.config_parameter'].search([('key', '=', key)])
            if ir_paramenter:
                number = int(ir_paramenter.value)
                rec.sequence_saft_invoice = "FT C" + str(date_start[0:4]) + "/" + str(number)
                ir_paramenter.value = number + 1

    def get_content_to_sign(self):
        domain = [('state', 'in', ['sale']), ]
        if self.env.user.has_group('base.group_multi_company'):
            domain.append(('company_id', '=', self.company_id.id))
        _last_sale_orders = self.env['sale.order'].search(
            domain, order='create_date asc').filtered(
            lambda r: r.date_order.strftime("%Y") == self.date_order.strftime("%Y"))
        if _last_sale_orders:
            if len(_last_sale_orders) > 1:
                last_sale_order = _last_sale_orders[-2]
                if last_sale_order:
                    total = utils.gross_total(self.amount_total)
                    content = (str(self.date_order.strftime("%Y-%m-%d")), str(self.system_entry_date).replace(
                        ' ', 'T'), self.name, str(total), last_sale_order.hash)
                    return ";".join(content)
            elif len(_last_sale_orders) == 1:
                total = utils.gross_total(self.amount_total)
                content = (
                    str(self.date_order.strftime("%Y-%m-%d")), str(self.system_entry_date).replace(' ', 'T'), self.name,
                    str(total))
                return ";".join(content) + ';'

    def action_confirm(self):
        result = super(SAFTSaleOrder, self).action_confirm()
        self.system_entry_date = fields.Datetime.now()
        if self.state == "sale":
            self.hash_control = self.company_id.key_version
            content_hash = self.get_content_to_sign()
            sequence_int = self.name.split('/')
            self.sequence_int = int(sequence_int[-1])
            content_signed = utils.signer(content_hash)
            if not content_signed:
                raise ValidationError(_("Problem Signing Invoice"))
            self.hash = content_signed
        return result
