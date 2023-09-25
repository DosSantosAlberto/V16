from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time


class ModelName(models.TransientModel):
    _name = 'supplier.map.wizard'
    _description = 'Supplier Map'

    start_date = fields.Date(string="Start Date",default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    end_date = fields.Date(string="End Date", default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()), )
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id,
                                 string="Company")

    @api.constrains('start_date', 'end_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("Start date cannot be greater than end date\n"
                                    " Please check dates."))

    def get_supplier(self):
        suppliers = []
        supplier = self.env['account.move'].search([("date", ">=", self.start_date),
                                                    ("date", "<=", self.end_date),
                                                    ('company_id', '=', self.company_id.id),
                                                    ('state', '=', 'posted'), ('move_type', '=', 'in_invoice')],
                                                   order="date asc")

        for record in supplier:
            data = {
                'name': record.partner_id.name,
                'ref': record.ref,
                'date': record.invoice_date,
                'type': "FT",
                'vat': record.partner_id.vat,
                'partner': record.partner_id,
                'reference': record.ref,
                'number': record.sequence_number,
                'order_number': record.name,
                'amount_total': record.amount_total,
                'amount_untaxed': record.amount_untaxed,
                'amount_tax': record.amount_tax,
            }
            suppliers.append(data)
        return suppliers

    def print(self):
        return self.env.ref('ht_account_ao.action_supplier_map_report').report_action(self)
