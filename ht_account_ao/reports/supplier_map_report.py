# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from dateutil.parser import parse
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class ReportSupplierMap(models.AbstractModel):
    _name = 'report.ht_account_ao.report_supplier_map_pdf'
    _description = "Supplier Map"

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data['form']['start_date']
        end_date = data['form']['end_date']
        company_id = data['form']['company_id'][0]

        local_context = dict(self.env.context, force_company=self.env.user.company_id.id, company_id=self.env.user.company_id.id)
        domain = [('invoice_date', '>=', start_date), ('invoice_date', '<=', end_date),
                  ('move_type', '=', 'in_invoice'), ('company_id', '=', company_id)]
        docs = self.env['account.move'].sudo().search(domain, order='invoice_date asc')
        print(docs)
        if not docs:
            raise ValidationError('There is no supplier map that match this criteria')

        return {
            'doc_ids': docs.ids,
            'results': docs,
            'end_date': end_date,
            'data': data['form'],
            'formatLang': formatLang,
            'company_id': company_id
        }
