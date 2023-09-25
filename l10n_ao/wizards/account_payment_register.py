# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class L10nAOAccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    amount_wth = fields.Monetary(_("Amount w/ Withhold"), currency_field='currency_id',
                                 compute="_compute_amount_withhold",
                                 store=True)
    wth_amount = fields.Monetary(_("Withhold Amount"),
                                 compute="_compute_amount_withhold",
                                 currency_field='currency_id',
                                 readonly=True, store=True)
    current_wth = fields.Monetary(_("Applied Withhold"), currency_field='currency_id',
                                  compute="_compute_amount_withhold",
                                  store=True)

    @api.depends("amount")
    def _compute_amount_withhold(self):
        amount_tax_wth = 0.0
        residual_rate = 1.0
        amount_wth_total = 0.0
        invoice_moves = self.env['account.move'].browse(self._context.get('active_ids', []))
        total_amount_residual = sum(invoice_moves.mapped("amount_residual"))
        for invoice in invoice_moves:
            residual_rate = 1 - (invoice.amount_total - invoice.amount_residual) / (invoice.amount_total or 1)
            invoice_amount_tax_wth = 0.0
            for line in invoice.invoice_line_ids:
                for tax in line.tax_ids:
                    tax_base_amount = line.price_unit * line.quantity
                    if tax.tax_exigibility == 'on_payment' and tax.is_withholding and \
                            tax_base_amount >= tax.threshold_wht:
                        # Tax amount.
                        tax_amount = tax._compute_amount(line.price_unit * line.quantity * (1 - (line.discount or 0.0) / 100.0), line.price_unit,
                                                         line.quantity)
                        amount_tax_wth += abs(tax_amount) * residual_rate
                        invoice_amount_tax_wth += abs(tax_amount) * residual_rate
            amount_wth_total += invoice.amount_residual - invoice_amount_tax_wth
        payment_rate = self.amount == 0.0 and 0.0 or (self.amount / (total_amount_residual - amount_tax_wth or 1))
        if amount_tax_wth == total_amount_residual:
            payment_rate = 0
        if payment_rate > 1:
            payment_rate = 1

        self.wth_amount = amount_tax_wth
        self.current_wth = amount_tax_wth * payment_rate
        self.amount_wth = amount_wth_total

    @api.depends('amount')
    def _compute_taxes_on_payment(self):
        for wizard in self:
            invoice_moves = self.env['account.move'].browse(self._context.get('active_ids', []))
            #calcular a razão do pagamento com base no valor em dívida.

            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                amount_wth = wizard.source_amount_currency - wizard.amount
            elif wizard.currency_id == wizard.company_id.currency_id:
                # Payment expressed on the company's currency.
                wizard.amount_wth = wizard.source_amount - wizard.amount
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount,
                                                                                 wizard.currency_id, wizard.company_id,
                                                                                 wizard.payment_date)
                #wizard.amount_wth = amount_payment_currency - wizard.amount

    @api.depends('amount')
    def _compute_payment_difference(self):
        for wizard in self:
            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                # AG: Adicionado a retencao a diferenca de pagamento
                wizard.payment_difference = wizard.source_amount_currency - wizard.amount - wizard.wth_amount
            elif wizard.currency_id == wizard.company_id.currency_id:
                # Payment expressed on the company's currency.
                wizard.payment_difference = wizard.source_amount - wizard.amount - wizard.wth_amount
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount,
                                                                                 wizard.currency_id, wizard.company_id,
                                                                                 wizard.payment_date)
                wizard.payment_difference = amount_payment_currency - wizard.amount - wizard.wth_amount

    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        amount_wth = 0.0

        if 'line_ids' in fields_list and 'line_ids' not in res:

            # Retrieve moves to pay from the context.
            if self._context.get('active_model') == 'account.move':
                lines = self.env['account.move'].browse(self._context.get('active_ids', [])).line_ids
            elif self._context.get('active_model') == 'account.move.line':
                lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
            else:
                raise UserError(_(
                    "The register payment wizard should only be called on account.move or account.move.line records."
                ))

            # Keep lines having a residual amount to pay.
            available_lines = self.env['account.move.line']
            for line in lines:
                if line.move_id.state != 'posted':
                    raise UserError(_("You can only register payment for posted journal entries."))

                if line.account_internal_type not in ('receivable', 'payable'):
                    continue
                if line.currency_id:
                    if line.currency_id.is_zero(line.amount_residual_currency):
                        continue
                else:
                    if line.company_currency_id.is_zero(line.amount_residual):
                        continue
                available_lines |= line

            # Check.
            if not available_lines:
                raise UserError(_(
                    "You can't register a payment because there is nothing left to pay on the selected journal items."))
            if len(lines.company_id) > 1:
                raise UserError(_("You can't create payments for entries belonging to different companies."))
            if len(set(available_lines.mapped('account_internal_type'))) > 1:
                raise UserError(
                    _("You can't register payments for journal items being either all inbound, either all outbound."))

            res['line_ids'] = [(6, 0, available_lines.ids)]

        moves = self.env['account.move'].browse(self._context.get('active_ids', []))
        for move in moves:
            amount_wth += move.amount_total_wth
        res['amount_wth'] = amount_wth
        return res

