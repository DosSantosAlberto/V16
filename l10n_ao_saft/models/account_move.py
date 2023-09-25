# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import utils
import requests
from datetime import datetime
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.tools.misc import formatLang


class SAFTAccountMove(models.Model):
    _inherit = 'account.move'

    hash = fields.Char(string="Key", default="0")
    hash_control = fields.Char(string="Key Version", relate='company_id.key_version')
    system_entry_date = fields.Datetime("Signature Datetime")
    settlement_discount = fields.Char(string="Settlement Discount")
    settlement_amount = fields.Float(string="Settlement Amount")
    settlement_date = fields.Date(string="Settlement Date")
    sequence_int = fields.Char('Sequence int')
    sequence_saft_invoice = fields.Char()

    transaction_type = fields.Selection(string="Tipo de Lançamento",
                                        required=True,
                                        selection=[('N', 'Normal'),
                                                   ('R', 'Regularizações'),
                                                   ('A', 'Apur. Resultados'),
                                                   ('J', 'Ajustamentos')],
                                        help="Categorias para classificar os movimentos contabilísticos ao exportar o SAFT",
                                        default="N", )

    tax_line_ids = fields.Many2one('account.tax', string='tax_line')

    @api.constrains('invoice_date')
    def _check_data_invoice(self):
        if self.move_type in ['out_invoice', 'out_refund']:
            invoices = self.env['account.move'].search(
                [('move_type', 'in', ['out_invoice', 'out_refund']), ('company_id', '=', self.company_id.id),
                 ('invoice_date', '>', self.invoice_date),
                 ('state', 'in', ['draft', 'posted'])],
                order="invoice_date")
            if invoices:
                ...
                #raise ValidationError(_(
                    #"There is already approved invoices whose date is higher than the one that is being inserted,"
                   # " you can not insert invoices, whose date is smaller than these"))

    def get_content_to_sign(self):
        domain = [
            ('state', 'in', ['posted']),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ]
        if self.env.user.has_group('base.group_multi_company'):
            domain.append(('company_id', '=', self.company_id.id))
        _last_invoices = self.env['account.move'].search(domain, order='invoice_date,name asc').filtered(
            lambda r: r.invoice_date.strftime("%Y") == self.invoice_date.strftime("%Y"))

        if _last_invoices:
            if len(_last_invoices) > 1:
                last_account_move = _last_invoices[-2]
                if last_account_move:
                    total = utils.gross_total(self.amount_total)

                    content = (str(self.invoice_date), str(self.system_entry_date).replace(
                        ' ', 'T'), self.name, str(total), last_account_move.hash)
                    return ";".join(content)
            elif len(_last_invoices) == 1:
                total = utils.gross_total(self.amount_total)
                content = (
                    str(self.invoice_date), str(self.system_entry_date).replace(' ', 'T'), self.name,
                    str(total))
                return ";".join(content) + ';'

    def action_post(self):
        result = super(SAFTAccountMove, self).action_post()
        if self.move_type in ['out_invoice', 'out_refund']:
            self.system_entry_date = fields.Datetime.now()
            if self.state == "posted":
                self.hash_control = self.company_id.key_version
                content_hash = self.get_content_to_sign()
                print(content_hash)
                sequence_int = self.name.replace('FT C', '').replace('FT F', '').split('/')
                self.sequence_int = sequence_int[-1]
                content_signed = utils.signer(content_hash)
                if not content_signed:
                    raise ValidationError(_("Problem Signing Invoice"))
                self.hash = content_signed
                print(self.hash)
        return result

    # def get_content_sign_saft(self, date_start, date_end):
    #     domain = [
    #         ('state', 'in', ['posted', ]),
    #         ('move_type', 'in', ['out_invoice']), ('invoice_date', '>=', date_start), ('invoice_date', '<=', date_end)
    #     ]
    #     if self.env.user.has_group('base.group_multi_company'):
    #         domain.append(('company_id', '=', self.company_id.id))
    #     invoices = self.search(domain, order='create_date asc')
    #     for j, rec in enumerate(invoices):
    #         print(j, "Contador de assinatura")
    #         if j == 0:
    #             total = utils.gross_total(rec.amount_total)
    #             content = (
    #                 str(rec.invoice_date), str((rec.create_date).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
    #                 rec.sequence_saft_invoice,
    #                 str(total))
    #             hash = ";".join(content) + ";"
    #             print(hash)
    #             hash = utils.signer(hash)
    #             print(hash)
    #             rec.hash = hash
    #         else:
    #             total = utils.gross_total(rec.amount_total)
    #             content = (
    #                 str(rec.invoice_date), str((rec.create_date).strftime("%Y-%m-%d %H:%M:%S")).replace(' ', 'T'),
    #                 rec.sequence_saft_invoice,
    #                 str(total), invoices[j].hash)
    #             hash = ";".join(content)
    #             print(hash)
    #             hash = utils.signer(hash)
    #             rec.hash = hash

    # def clean_number_invoices(self, date_start, date_end):
    #     domain = [('state', 'in', ['posted', ]), ('move_type', 'in', ['out_invoice']),
    #               ('invoice_date', '>=', date_start), ('invoice_date', '<=', date_end)]
    #     invoices = self.search(domain, order='invoice_date asc')
    #     for rec in invoices:
    #         ir_paramenter = self.env['ir.config_parameter'].search([('key', '=', 'cp.satf.sequence.invoice')])
    #         account_payment = self.env['account.payment'].search([("ref", '=', rec.name)], order='date desc')
    #         if ir_paramenter:
    #             number = int(ir_paramenter.value)
    #             rec.sequence_saft_invoice = "FT C" + str(date_start).split('-')[0] + "/" + '%0*d' % (
    #                 3, number)
    #             for payment in account_payment:
    #                 payment.sequence_saft_rf = "RG " + str(date_start).split('-')[
    #                     0] + "/" + '%0*d' % (
    #                                                3, number)
    #                 print("RG " + str(date_start).split('-')[
    #                     0] + "/" + '%0*d' % (
    #                           3, number))
    #                 break
    #             ir_paramenter.value = number + 1
    #         rec.get_content_to_sign()
    #
    #     for rec in invoices:
    #         rec.get_content_sign_saft(date_start, date_end)
    #         break
    #
    #     for rec in invoices:
    #         print(rec.sequence_saft_invoice, rec.hash)
