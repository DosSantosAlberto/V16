# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2022 Eletic Solution Lda, Lda. All Rights Reserved
# http://www.eletic-solution.com.

from odoo import api, models, fields, _
import os

from PyPDF2 import PdfReader, PdfWriter


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.es_account_report_ao.report_trial_balance_ao'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'data': data['form'],
        }

    def test_data(self):

        temp = self.env['ir.attachment'].search([])
        for i in temp:
            if i.name == 'dharmik.pdf':
                print(i.name)

    def get_current_page_number(self):
        pdf_file = open("account_financial_balance.pdf", "rb")
        pdf_reader = PdfFileReader(pdf_file)
        print(pdf_reader.getOutlines())


    #def get_current_page_number(html):
      #  match = re.search(r'<span class="current-comment-page">\[(.*)\]</span>', html)
      #  return match.group(1)

   # md(f"# {ticker} Report {datetime.now().strftime('%m-%d-%Y')}")

   # def test_data(self):
#
       # temp = self.env['ir.attachment'].search([])
        #for i in temp:
         #   if i.name == 'dharmik.pdf':
              #  print(i.name)

