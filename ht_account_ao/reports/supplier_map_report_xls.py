from odoo import models


class AccountInvoiceXlsx(models.AbstractModel):
    _name = 'report.l10n_ao.report_supplier_map_xls'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, model):
        count_line = 4
        count_inv = 1
        sheet = workbook.add_worksheet('Mapa de Fornecedores')
        format1 = workbook.add_format({'font_size': 12, 'align': 'center', 'bold': True})
        format2 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        workbook.columnize = 10
        sheet.write(0, 0, model.company_id.vat, format1)
        sheet.write(1, 0, model.start_date[:7], format1)
        sheet.write(3, 0, 'Nº Ordem', format1)
        sheet.write(3, 1, 'Nº de Identificação Fiscal', format1)
        sheet.write(3, 2, 'Nome / Firma', format1)
        sheet.write(3, 3, 'Tipo de Documento', format1)
        sheet.write(3, 4, 'Valor da Factura', format1)
        sheet.write(3, 5, 'Valor Tributável', format1)
        sheet.write(3, 6, 'IVA Suportado', format1)

        for inv in model.get_invoice():
            sheet.write(count_line, 0, count_inv, format2)
            sheet.write(count_line, 1, inv.partner_id.vat, format2)
            sheet.write(count_line, 2, inv.company_id.name, format2)
            sheet.write(count_line, 3, 'FT', format2)
            sheet.write(count_line, 4, inv.amount_total, format2)
            sheet.write(count_line, 5, inv.amount_untaxed, format2)
            sheet.write(count_line, 6, inv.amount_tax, format2)
            count_line += 1
            count_inv += 1
