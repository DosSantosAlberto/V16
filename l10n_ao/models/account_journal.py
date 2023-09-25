import math
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import re


class AccountJournalAO(models.Model):
    _inherit = "account.journal"

    self_billing = fields.Boolean(string="Auto-Facturação",
                                  help='''Assinale, se este diário se destina a registar Auto-facturação.
              As facturas emitidas em substituição dos fornecedores, ao abrigo de acordos de auto-facturação,
               são assinaladas como tal no SAFT''')
    saft_invoice_type = fields.Selection([('FT', 'Factura'),
                                          ('ND', 'Nota de débito'),
                                          ('NC', 'Nota de Crédito'),
                                          ('VD', 'Venda a Dinheiro'),
                                          ('AA', 'Alienação de Activos'),
                                          ('DA', 'Devolução de Activos')], required=False,
                                         help="Category to classify document for SAFT-AO",
                                         default="FT", )
    document_type = fields.Selection([('FT', 'Factura'), ('FR', 'Factura Recibo'), ('VD', 'Venda a Dinheiro'),
                                      ], string="Document Type")
    payment_mechanism = fields.Selection(string="Payment Mechanism",
                                         selection=[('CC', 'Cartão crédito'), ('CD', 'Cartão débito'),
                                                    ('CI', 'Crédito documentário internacional'),
                                                    ('CO', 'Cheque ou cartão oferta'),
                                                    ('CS', 'Compensação de saldos em conta corrente'),
                                                    ('DE',
                                                     'Dinheiro electrónico,por exemplo residente em cartões de fidelidade ou de pontos'),
                                                    ('MB', 'Referências de pagamento para Multicaixa'),
                                                    ('NU', 'Numerário'),
                                                    ('OU', 'Outros meios aqui não assilados'),
                                                    ('PR', 'Permuta de bens'),
                                                    ('TB', 'Transferência bancária')])

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, company_id)',
         'The code and name of the journal must be unique per company !'),
    ]

    @api.onchange("document_type")
    def check_code_type(self):
        if self.document_type and self.document_type == 'FT':
            self.code = 'FT'
        elif self.document_type and self.document_type == 'FR':
            self.code = 'FR'

    @api.model
    def _get_sequence_prefix(self, code, refund=False):
        prefix = code.upper()
        if refund and "FT" in code:
            prefix = 'NC '
        if refund and "FTF" in code:
            prefix = 'ND '
        return prefix + '%(range_year)s/'

    @api.model
    def _create_sequence(self, vals, refund=False):
        """ Create new no_gap entry sequence for every new Journal"""
        prefix = self._get_sequence_prefix(vals['code'], refund)
        seq_name = refund and vals['code'] + _(': Refund') or vals['code']
        if refund and (vals.get('type') == 'sale' or self.type == 'sale'):
            seq_name = 'NC'
        if refund and (vals.get('type') == 'purchase' or self.type == 'purchase'):
            seq_name = 'ND'
        seq = {
            'name': _('%s Sequence') % seq_name,
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 0,
            'number_increment': 1,
            'use_date_range': True,
        }

        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        seq = self.env['ir.sequence'].create(seq)
        seq_date_range = seq._get_current_sequence()
        seq_date_range.number_next = refund and vals.get('refund_sequence_number_next', 1) or vals.get(
            'sequence_number_next', 1)
        return seq

    def get_saft_data(self):
        start_date = self._context.get("start_date")
        end_date = self._context.get("end_date")

        if not start_date or not end_date:
            raise ValidationError(_("Start date or end period date are not defined!"))

        result = {
            "GeneralLedgerEntries": {
                "NumberOfEntries": len(self),
                "TotalDebit": 0,
                "TotalCredit": 0,
                "Journal": [],
            },
        }
        total_debit = total_credit = 0.0

        for journal in self:
            journal_moves = self.env["account.move"].search(
                [("journal_id", "=", journal.id), ("date", ">=", fields.Date.to_string(start_date)),
                 ("date", "<=", fields.Date.to_string(end_date)),
                 ("state", "=", "posted")])
            total_debit += sum(journal_moves.mapped("line_ids.debit"))
            total_credit += sum(journal_moves.mapped("line_ids.credit"))

            if not journal_moves:
                continue

            journal_val = {
                "JournalID": journal.code,
                "Description": journal.name,
                "Transaction": [
                    {
                        "TransactionID": move.name,
                        "Period": fields.Date.to_string(move.date)[5:7],
                        "TransactionDate": fields.Date.to_string(move.date)[5:7],
                        "SourceID": move.create_uid.id,
                        "Description": move.ref if move.ref else "",
                        "DocArchivalNumber": move.ref if move.ref else "",
                        "TransactionType": move.transaction_type,
                        "GLPostingDate": fields.Date.to_string(move.write_date),
                        "CustomerID": move.partner_id.id if move.journal_id.type == "sale" else "",
                        "SupplierID": move.partner_id.id if move.journal_id.type == "purchase" else "",
                        "Lines": {
                            "DebitLine": [{
                                "RecordID": line.id,
                                "AccountID": line.account_id.code,
                                "SourceDocumentID": line.invoice_id.number if line.invoice_id else line.ref or "",
                                "SystemEntryDate": fields.Datetime.to_string(line.date),
                                "Description": line.name,
                                "DebitAmount": line.debit,
                            } for line in move.line_ids if line.debit > 0.0],
                            "CreditLine": [{
                                "RecordID": line.id,
                                "AccountID": line.account_id.code,
                                "SourceDocumentID": line.invoice_id.number if line.invoice_id else line.ref or "",
                                "SystemEntryDate": fields.Datetime.to_string(line.date),
                                "Description": line.name,
                                "CreditAmount": line.credit,
                            } for line in move.line_ids if line.credit > 0.0],
                        },
                    } for move in journal_moves],
            }
            result["GeneralLedgerEntries"]["Journal"].append(journal_val)

        result["GeneralLedgerEntries"]["TotalDebit"] = round(total_debit, 2)
        result["GeneralLedgerEntries"]["TotalCredit"] = round(total_credit, 2)
        return result

    def write(self, vals):
        if self[0].company_id.country_id.code == "AO":
            if vals.get('type') in ['sale', 'purchase']:
                self.write({'refund_sequence': True, "restrict_mode_hash_table": True})
            if re.search(r"\s", str(vals.get("code"))):
                raise ValidationError(
                    _("O código curto não pode ter espaço. Por favor Retire qualquer espaço que tenha adicionado!"))
            # if vals.get("code") and self[0].type == 'sale':
            #     vals['code'] = "%s %s" % (self[0].document_type, vals.get("code"))
            # if vals.get("code") and self[0].type == 'purchase':
            #     vals['code'] = "%s %s" % ("FTF", vals.get("code"))
        result = super(AccountJournalAO, self).write(vals)

    @api.model
    def create(self, vals):
        journal = super(AccountJournalAO, self).create(vals)
        if vals.get('type') in ['sale', 'purchase'] and journal.company_id.country_id.code == "AO":
            journal.write({'refund_sequence': True, "restrict_mode_hash_table": True})
        return journal
