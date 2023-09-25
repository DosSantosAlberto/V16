# -*- coding: utf-8 -*-

from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, float_is_zero, date_utils, email_split, email_re, html_escape, is_html_empty
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from contextlib import contextmanager
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_total_wth = fields.Monetary(string='Total w/ Withhold', readonly=True, store=True,
                                       compute='_compute_amount_total_wth')
    amount_wth_apply = fields.Monetary(string='Applied Withholding', readonly=True, store=True,
                                       compute='_compute_amount_total_wth')
    partner_deductible_vat = fields.Selection([
        ('none', 'Does not deduct'),
        ('state', 'State'),
        ('it', 'Information Technology'),
        ('bank', 'Banking Institutions')
    ], string="Partner Deductible Vat", default='none')

    @api.depends('amount_total')
    def _compute_amount_total_wth(self):
        """calcul withholding amount - @author: Hermenegildo Mulonga """
        _withholding = self.get_withholding_tax()
        _amount_wht = 0.0
        if _withholding > 0.0:
            for res in self:
                if res.journal_id.type in ['sale', 'purchase']:
                    _amount_wht = res.amount_total - _withholding
                    res.amount_total_wth = _amount_wht
                    res.amount_wth_apply = _withholding
        return _withholding

    def get_withholding_tax(self):
        """return:  amount total tax withholding - @author: Hermenegildo Mulonga """
        withholding_tax_amount = 0
        for line in self.get_tax_line_details():
            if line['tax_exigibility'] == 'withholding':
                withholding_tax_amount += line['tax_amount']
        return withholding_tax_amount

    def _prepare_tax_lines_data_for_totals_from_invoice(self, tax_line_id_filter=None, tax_ids_filter=None):
        """ Prepares data to be passed as tax_lines_data parameter of _get_tax_totals() from an invoice.

            NOTE: tax_line_id_filter and tax_ids_filter are used in l10n_latam to restrict the taxes with consider
                  in the totals.

            :param tax_line_id_filter: a function(aml, tax) returning true if tax should be considered on tax move line aml.
            :param tax_ids_filter: a function(aml, taxes) returning true if taxes should be considered on base move line aml.

            :return: A list of dict in the format described in _get_tax_totals's tax_lines_data's docstring.
        """
        self.ensure_one()

        tax_line_id_filter = tax_line_id_filter or (lambda aml, tax: True)
        tax_ids_filter = tax_ids_filter or (lambda aml, tax: True)

        balance_multiplicator = -1 if self.is_inbound() else 1
        tax_lines_data = []

        for line in self.line_ids:
            if line.tax_line_id.tax_exigibility in ['on_invoice']:
                if line.tax_line_id and tax_line_id_filter(line, line.tax_line_id):
                    tax_lines_data.append({
                        'line_key': 'tax_line_%s' % line.id,
                        'tax_amount': line.amount_currency * balance_multiplicator,
                        'tax': line.tax_line_id,
                    })

            if line.tax_ids:
                for base_tax in line.tax_ids.flatten_taxes_hierarchy():
                    if base_tax.tax_exigibility in ['on_invoice']:
                        if tax_ids_filter(line, base_tax):
                            tax_lines_data.append({
                                'line_key': 'base_line_%s' % line.id,
                                'base_amount': line.amount_currency * balance_multiplicator,
                                'tax': base_tax,
                                'tax_affecting_base': line.tax_line_id,
                            })

        return tax_lines_data

    @api.model
    def _prepare_tax_lines_data_for_totals_from_object(self, object_lines, tax_results_function):
        """ Prepares data to be passed as tax_lines_data parameter of _get_tax_totals() from any
            object using taxes. This helper is intended for purchase.order and sale.order, as a common
            function centralizing their behavior.

            :param object_lines: A list of records corresponding to the sub-objects generating the tax totals
                                 (sale.order.line or purchase.order.line, for example)

            :param tax_results_function: A function to be called to get the results of the tax computation for a
                                         line in object_lines. It takes the object line as its only parameter
                                         and returns a dict in the same format as account.tax's compute_all
                                         (most probably after calling it with the right parameters).

            :return: A list of dict in the format described in _get_tax_totals's tax_lines_data's docstring.
        """
        tax_lines_data = []

        for line in object_lines:
            tax_results = tax_results_function(line)

            for tax_result in tax_results['taxes']:
                current_tax = self.env['account.tax'].browse(tax_result['id'])
                """only invoice tax, @author: Hermenegildo Mulonga / Halow Tecnology """
                if current_tax.tax_exigibility in ['on_invoice']:

                    # Tax line
                    tax_lines_data.append({
                        'line_key': f"tax_line_{line.id}_{tax_result['id']}",
                        'tax_amount': tax_result['amount'],
                        'tax': current_tax,
                    })

                    # Base for this tax line
                    tax_lines_data.append({
                        'line_key': 'base_line_%s' % line.id,
                        'base_amount': tax_results['total_excluded'],
                        'tax': current_tax,
                    })

                    # Base for the taxes whose base is affected by this tax line
                    if tax_result['tax_ids']:
                        affected_taxes = self.env['account.tax'].browse(tax_result['tax_ids'])
                        for affected_tax in affected_taxes:
                            tax_lines_data.append({
                                'line_key': 'affecting_base_line_%s_%s' % (line.id, tax_result['id']),
                                'base_amount': tax_result['amount'],
                                'tax': affected_tax,
                                'tax_affecting_base': current_tax,
                            })
        return tax_lines_data

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        ''' Recompute all lines that depend on others.

        For example, tax lines depends on base lines (lines having tax_ids set). This is also the case of cash rounding
        lines that depend on base lines or tax lines depending on the cash rounding strategy. When a payment term is set,
        this method will auto-balance the move with payment term lines.

        :param recompute_all_taxes: Force the computation of taxes. If set to False, the computation will be done
                                    or not depending on the field 'recompute_tax_line' in lines.
        '''
        for invoice in self:
            # Dispatch lines and pre-compute some aggregated values like taxes.
            expected_tax_rep_lines = set()
            current_tax_rep_lines = set()
            inv_recompute_all_taxes = recompute_all_taxes
            to_remove = self.env['account.move.line']
            for line in invoice.line_ids:
                """only invoice tax, @author: Hermenegildo Mulonga / Halow Tecnology """
                if line.tax_repartition_line_id.tax_id.tax_exigibility in ['on_payment', 'withholding']:
                    to_remove += line
                if line.recompute_tax_line:
                    inv_recompute_all_taxes = True
                    line.recompute_tax_line = False
                if line.tax_repartition_line_id:
                    current_tax_rep_lines.add(line.tax_repartition_line_id._origin)
                elif line.tax_ids:
                    if invoice.is_invoice(include_receipts=True):
                        is_refund = invoice.move_type in ('out_refund', 'in_refund')
                    else:
                        tax_type = line.tax_ids[0].type_tax_use
                        is_refund = (tax_type == 'sale' and line.debit) or (tax_type == 'purchase' and line.credit)
                    taxes = line.tax_ids._origin.flatten_taxes_hierarchy().filtered(
                        lambda tax: (
                                tax.amount_type == 'fixed' and not invoice.company_id.currency_id.is_zero(tax.amount)
                                or not float_is_zero(tax.amount, precision_digits=4)
                        )
                    )
                    if is_refund:
                        tax_rep_lines = taxes.refund_repartition_line_ids._origin.filtered(
                            lambda x: x.repartition_type == "tax")
                    else:
                        tax_rep_lines = taxes.invoice_repartition_line_ids._origin.filtered(
                            lambda x: x.repartition_type == "tax")
                    for tax_rep_line in tax_rep_lines:
                        expected_tax_rep_lines.add(tax_rep_line)
            delta_tax_rep_lines = expected_tax_rep_lines - current_tax_rep_lines
            invoice.line_ids -= to_remove

            # Compute taxes.
            if inv_recompute_all_taxes:
                invoice._recompute_tax_lines()
            elif recompute_tax_base_amount:
                invoice._recompute_tax_lines(recompute_tax_base_amount=True)
            # elif delta_tax_rep_lines and not self._context.get('move_reverse_cancel'):
            #     invoice._recompute_tax_lines(tax_rep_lines_to_recompute=delta_tax_rep_lines)

            if invoice.is_invoice(include_receipts=True):

                # Compute cash rounding.
                invoice._recompute_cash_rounding_lines()

                # Compute payment terms.
                invoice._recompute_payment_terms_lines()

                # Only synchronize one2many in onchange.
                if invoice != invoice._origin:
                    invoice.invoice_line_ids = invoice.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)
