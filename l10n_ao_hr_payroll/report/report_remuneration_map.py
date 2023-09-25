# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from dateutil.parser import parse
from odoo.exceptions import ValidationError, UserError
from xml.dom.minidom import parseString
from dicttoxml2 import dicttoxml
import base64, os, tempfile
import xlsxwriter
import urllib.parse
import werkzeug
import requests


class ReportRemunerationMap(models.AbstractModel):
    _name = 'report.l10n_ao_hr_payroll.report_remuneration_map'
    _description = 'Remuneration Map'

    def remuneration_map_report(self, docids, report_file, data=None):  # -d hr_payroll -u l10n_ao_hr_payroll
        docs = None
        period_date_obj = None
        if 'form' not in data:
            raise ValidationError('This action is under development')

        slip_filter_by = data['form']['slip_filter_by']
        if slip_filter_by == 'payslip_batch':
            slip_id = data['form']['hr_payslip_run_id'][0]
            docs = self.env['hr.payslip'].search(
                [('payslip_run_id', '=', slip_id), ('company_id', '=', self.env.company.id), ('state', '=', 'done')],
                order="employee_id")
            period_date = self.env['hr.payslip.run'].browse(slip_id).date_end
        else:
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            if type(end_date) is str:
                period_date = parse(end_date)
            else:
                period_date = end_date
            docs = self.env['hr.payslip'].search(
                [('date_to', '>=', start_date), ('date_to', '<=', end_date), ('company_id', '=', self.env.company.id),
                 ('state', '=', 'done')], order="employee_id")

        if not docs:
            raise ValidationError('There is no payslips that match this criteria')

        months = {1: _('01'), 2: _('02'), 3: _('03'), 4: _('04'), 5: _('05'), 6: _('06'), 7: _('07'), 8: _('08'),
                  9: _('09'), 10: _('10'), 11: _('11'), 12: _('12'), }

        def create_remuneration_dict(period, docs):
            remuneration_map_dict = {}
            remuneration_map_dict["MapaRemuneracoes"] = {
                "AgenteRetencao": {'strNifAgente': self.env.company.vat, 'strAnoMes': period}}
            remuneration_map_dict["MapaRemuneracoes"]['Remuneracao'] = []
            for doc in docs:
                values = {}
                values["strNifFuncionario"] = doc.employee_id.fiscal_number if doc.employee_id.fiscal_number else ''
                values["strNomeFuncionario"] = doc.employee_id.name
                values["strNumSS"] = doc.employee_id.social_security if doc.employee_id.social_security else ''
                values["strProvincia"] = doc.employee_id.address_province if doc.employee_id.address_province else ''
                values["strMunicipio"] = doc.employee_id.address_county if doc.employee_id.address_county else ''
                values["decSalarioBase"] = doc.contract_id.wage if doc.contract_id.wage else ''
                decDescontoFaltas = decAlimentacao = decTransporte = decAbonoFamilia = decOutros = decAbonoFalhas = 0
                decSubsidioRepresentacao = decSubsidioAtavio = decHorasExtras = decSubsidioFerias = decCompensacaoRescisao = 0
                decRendaCasa = decReembolsoDespesas = decPremios = decSubsidioNatal = decOutrosSubsidiosSujeitos = decSubsidioChefia = 0
                for line in doc.line_ids:
                    if 'FALTA' == line.code:
                        decDescontoFaltas = abs(line.total)
                    elif 'ALIM' == line.code:
                        decAlimentacao = abs(line.total)
                    elif 'TRAN' == line.code:
                        decTransporte = abs(line.total)
                    elif 'FAMI' in line.code:
                        decAbonoFamilia = abs(line.total)
                    elif 'FALH' in line.code:
                        decAbonoFalhas = abs(line.total)
                    elif 'RENDES' in line.code:
                        decReembolsoDespesas = abs(line.total)
                    elif 'sub_ren_casa' in line.code:
                        decRendaCasa = line.total
                    elif 'CORES' in line.code:
                        decCompensacaoRescisao = abs(line.total)
                    elif 'FER' in line.code:
                        decSubsidioFerias = abs(line.total)
                    elif 'sub_not' in line.code:
                        decHorasExtras = abs(line.total)
                    elif 'ATA' in line.code:
                        decSubsidioAtavio = abs(line.total)
                    elif 'REPR' in line.code:
                        decSubsidioRepresentacao = abs(line.total)
                    elif 'PREM' in line.code:
                        decPremios = abs(line.total)
                    elif 'NAT' in line.code:
                        decSubsidioNatal = abs(line.total)
                    elif 'CHEF' in line.code:
                        decSubsidioChefia = abs(line.total)

                    if line.category_id.code in ['ALW', "ABO", "DED"]:
                        if line.code not in ['BASE', 'CHEF', 'NAT', 'PREM', 'REPR', 'ATA', 'sub_not', 'FER',
                                             'CORES', 'sub_ren_casa', 'RENDES', 'FALH', 'FAMI', 'TRAN', 'ALIM',
                                             'FALTA']:
                            decOutros += abs(line.total)

                    if line.category_id.code in ['COMP', "ABOIRT", "ABOINSSIRT", "DEDINSSIRT"]:
                        if line.code not in ['BASE', 'CHEF', 'NAT', 'PREM', 'REPR', 'ATA', 'sub_not', 'FER',
                                             'CORES', 'sub_ren_casa', 'RENDES', 'FALH', 'FAMI', 'TRAN', 'ALIM',
                                             'FALTA']:
                            decOutrosSubsidiosSujeitos += abs(line.total)

                values["decDescontoFaltas"] = decDescontoFaltas
                values["SubsidiosNaoSujeitosIRT"] = {"decAlimentacao": decAlimentacao, "decTransporte": decTransporte,
                                                     "decAbonoFamilia": decAbonoFamilia,
                                                     "decReembolsoDespesas": decReembolsoDespesas,
                                                     "decOutros": decOutros}
                values["strManualExcSubsNaoSujeitosIRT"] = 'N'
                values["decExcSubsNaoSujeitosIRT"] = 0
                values["SubsidiosSujeitosIRT"] = {"decAbonoFalhas": decAbonoFalhas, "decRendaCasa": decRendaCasa,
                                                  "decCompensacaoRescisao": decCompensacaoRescisao,
                                                  "decSubsidioFerias": decSubsidioFerias,
                                                  "decHorasExtras": decHorasExtras,
                                                  "decSubsidioAtavio": decSubsidioAtavio,
                                                  "decSubsidioRepresentacao": decSubsidioRepresentacao,
                                                  "decPremios": decPremios, "decSubsidioNatal": decSubsidioNatal,
                                                  "decOutrosSubsidiosSujeitos": decOutrosSubsidiosSujeitos}
                values["decSalarioIliquido"] = 0
                values["strManualBaseTributavelSS"] = "N"
                values["decBaseTributavelSS"] = 0
                values["strIsentoSS"] = "N"
                values["decContribuicaoSS"] = 0
                values["decBaseTributavelIRT"] = 0
                values["strIsentoIRT"] = "N"
                values["decIRTApurado"] = 0

                remuneration_map_dict["MapaRemuneracoes"]['Remuneracao'].append(values)
            return remuneration_map_dict

        def get_xlsx_dict_values(docs):
            data_values = []
            index = 5
            # Payslip Values
            for doc in docs:
                values = {}
                values[f'A{index}'] = doc.employee_id.fiscal_number if doc.employee_id.fiscal_number else ''
                values[f'B{index}'] = doc.employee_id.name
                values[f'C{index}'] = doc.employee_id.social_security if doc.employee_id.social_security else ''
                values[f'D{index}'] = doc.employee_id.address_province if doc.employee_id.address_province else ''
                values[f'E{index}'] = doc.employee_id.address_county if doc.employee_id.address_county else ''
                values[f'F{index}'] = doc.contract_id.wage if doc.contract_id.wage else ''
                decDescontoFaltas = decAlimentacao = decTransporte = decAbonoFamilia = decOutros = decAbonoFalhas = 0.0
                decSubsidioRepresentacao = decSubsidioAtavio = decHorasExtras = decSubsidioFerias = decCompensacaoRescisao = decSubsidioChefia = 0.0
                decRendaCasa = decReembolsoDespesas = decPremios = decSubsidioNatal = decOutrosSubsidiosSujeitos = decPremio = 0.0
                for line in doc.line_ids:
                    if 'FALTA' == line.code:
                        decDescontoFaltas = abs(line.total)
                    elif 'ALIM' == line.code:
                        decAlimentacao = abs(line.total)
                    elif 'TRAN' == line.code:
                        decTransporte = abs(line.total)
                    elif 'FAMI' in line.code:
                        decAbonoFamilia = abs(line.total)
                    elif 'FALH' in line.code:
                        decAbonoFalhas = abs(line.total)
                    elif 'RENDES' in line.code:
                        decReembolsoDespesas = abs(line.total)
                    elif 'sub_ren_casa' in line.code:
                        decRendaCasa = line.total
                    elif 'CORES' in line.code:
                        decCompensacaoRescisao = abs(line.total)
                    elif 'FER' in line.code:
                        decSubsidioFerias = abs(line.total)
                    elif 'sub_not' in line.code:
                        decHorasExtras = abs(line.total)
                    elif 'ATA' in line.code:
                        decSubsidioAtavio = abs(line.total)
                    elif 'REPR' in line.code:
                        decSubsidioRepresentacao = abs(line.total)
                    elif 'PREM' in line.code:
                        decPremios = abs(line.total)
                    elif 'NAT' in line.code:
                        decSubsidioNatal = abs(line.total)
                    elif 'CHEF' in line.code:
                        decSubsidioChefia = abs(line.total)

                    if line.category_id.code in ['ALW', "ABO", "DED"]:
                        if line.code not in ['BASE', 'CHEF', 'NAT', 'PREM', 'REPR', 'ATA', 'sub_not', 'FER',
                                             'CORES', 'sub_ren_casa', 'RENDES', 'FALH', 'FAMI', 'TRAN', 'ALIM',
                                             'FALTA']:
                            decOutros += abs(line.total)

                    if line.category_id.code in ['COMP', "ABOIRT", "ABOINSSIRT", "DEDINSSIRT"]:
                        if line.code not in ['BASE', 'CHEF', 'NAT', 'PREM', 'REPR', 'ATA', 'sub_not', 'FER',
                                             'CORES', 'sub_ren_casa', 'RENDES', 'FALH', 'FAMI', 'TRAN', 'ALIM',
                                             'FALTA']:
                            decOutrosSubsidiosSujeitos += abs(line.total)

                values[f'G{index}'] = decDescontoFaltas
                values[f'H{index}'] = decAlimentacao
                values[f'I{index}'] = decTransporte
                values[f'J{index}'] = decAbonoFamilia
                values[f'K{index}'] = decReembolsoDespesas
                values[f'L{index}'] = decOutros
                values[f'M{index}'] = 'N'
                values[f'N{index}'] = 0.0
                values[f'O{index}'] = decAbonoFalhas
                values[f'P{index}'] = decRendaCasa
                values[f'Q{index}'] = decCompensacaoRescisao
                values[f'R{index}'] = decSubsidioFerias
                values[f'S{index}'] = decHorasExtras
                values[f'T{index}'] = decSubsidioAtavio
                values[f'U{index}'] = decSubsidioRepresentacao
                values[f'V{index}'] = decPremios
                values[f'W{index}'] = decSubsidioNatal
                values[f'X{index}'] = decSubsidioChefia
                values[f'Y{index}'] = decOutrosSubsidiosSujeitos
                values[f'Z{index}'] = 0.0
                values[f'AA{index}'] = "N"
                values[f'AB{index}'] = 0.0
                values[f'AC{index}'] = "N"
                values[f'AD{index}'] = 0.0
                values[f'AE{index}'] = 0.0
                values[f'AF{index}'] = "N"
                values[f'AG{index}'] = 0.0

                data_values.append(values)
                index += 1

            return data_values

        def create_temp_xlsx_file(period, docs):
            # create remuneration temp file
            temp_file = tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix=".xls")
            dir_path = temp_file.name
            file = temp_file.name.split('/')
            file[-1] = f"REMUNERATION_MAP_PERIOD_{period}.xls"
            new_dir_path = '/'.join(map(str, file))
            os.rename(dir_path, new_dir_path)
            # Write file XLSX
            workbook = xlsxwriter.Workbook(new_dir_path)
            worksheet = workbook.add_worksheet()
            cell_format = workbook.add_format(
                {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#808080'})
            cell_format.set_font_color('#000000')
            color_format_silver = workbook.add_format(
                {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#A9A9A9', })
            color_format_silver.set_font_color('#191970')
            color_format_black = workbook.add_format(
                {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#808080'})
            color_format_black.set_font_color('#000000')
            color_format_white = workbook.add_format(
                {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#e9ecef'})
            color_format_white.set_font_color('#000000')
            # Header
            # BODY
            worksheet.write_string('A1', self.env.company.vat, color_format_white)
            worksheet.write_string('A2', period, color_format_white)
            worksheet.write_string('B1', "NIF do Contribuinte", color_format_black)
            worksheet.set_column('B1:B1', 25)  # Column Widths
            worksheet.write_string('B2', "Período (AAAA-MM)", color_format_black)
            worksheet.set_column('B2:B2', 25)  # Column Widths

            worksheet.write_string('A4', "NIF Trabalhador", color_format_black)
            worksheet.set_column('A4:A4', 15)  # Column Widths
            worksheet.write_string('B4', "Nome", color_format_black)
            worksheet.write_string('C4', "Nº Segurança Social", color_format_black)
            worksheet.set_column('C4:C4', 15)  # Column Widths
            worksheet.write_string('D4', "Província", color_format_black)
            worksheet.set_column('D4:D4', 10)  # Column Widths
            worksheet.write_string('E4', "Município", color_format_black)
            worksheet.set_column('E4:E4', 10)  # Column Widths
            worksheet.write_string('F4', "Salário Base", color_format_black)
            worksheet.set_column('F4:F4', 10)  # Column Widths
            worksheet.write_string('G4', "Descontos por Falta", color_format_black)
            worksheet.set_column('G4:G4', 15)  # Column Widths
            worksheet.set_column('C3:L3', 35)  # Column Widths
            worksheet.set_column('O3:X3', 35)  # Column Widths
            worksheet.write_string('H4', "Subsídio Alimentação", color_format_silver)
            worksheet.write_string('I4', "Subsídio Transporte", color_format_silver)
            worksheet.write_string('J4', "Abono Família", color_format_silver)
            worksheet.write_string('K4', "Reembolso de Despesas", color_format_silver)
            worksheet.write_string('L4', "Outros", color_format_silver)
            worksheet.write_string('O4', "Abono de Falhas", color_format_silver)
            worksheet.write_string('P4', "Subsídio Renda de Casa", color_format_silver)
            worksheet.write_string('Q4', "Compensação Por Rescisão", color_format_silver)
            worksheet.write_string('R4', "Subsídio de Férias", color_format_silver)
            worksheet.write_string('S4', "Horas Extras", color_format_silver)
            worksheet.write_string('T4', "Subsídio de Atavio", color_format_silver)
            worksheet.write_string('U4', "Subsídio de Representação", color_format_silver)
            worksheet.write_string('V4', "Prémios", color_format_silver)
            worksheet.write_string('W4', "Subsídio de Natal", color_format_silver)
            worksheet.write_string('X4', "Subsídio de Chefia", color_format_silver)
            worksheet.write_string('Y4', "Outros Subsídios Sujeitos", color_format_silver)
            worksheet.set_column('Y4:Y4', 30)
            # HEADER: MERGE COLUMN
            worksheet.merge_range('M3:M4', "", cell_format)
            worksheet.write_string('M3', 'Cálculo Manual de Excesso de Subsídios?', cell_format)
            worksheet.set_column('M3:M3', 40)  # Column Widths
            worksheet.merge_range('N3:N4', "", cell_format)
            worksheet.write_string('N3', 'Excesso Subsídios Não Sujeitos', cell_format)
            worksheet.set_column('N3:N3', 30)
            worksheet.merge_range('H3:L3', "", cell_format)
            worksheet.write_string('H3', 'Subsídios Não Sujeitos a IRT (Art. 2º do CIRT)', cell_format)
            worksheet.merge_range('O3:Y3', "", cell_format)
            worksheet.write_string('O3', 'Subsídios Sujeitos a IRT ', cell_format)
            worksheet.merge_range('Z3:Z4', "", cell_format)
            worksheet.write_string('Z3', 'Salário Ilíquido', cell_format)
            worksheet.set_column('Z3:Z3', 25)  # Column Widths
            worksheet.merge_range('AA3:AA4', "", cell_format)
            worksheet.write_string('AA3', 'Cálculo Manual da Base Trib. Seg. Social?', cell_format)
            worksheet.set_column('AA3:AA3', 45)  # Column Widths
            worksheet.merge_range('AB3:AB4', "", cell_format)
            worksheet.write_string('AB3', 'Base Tributável Segurança Social', cell_format)
            worksheet.set_column('AB3:AB3', 35)  # Column Widths
            worksheet.merge_range('AC3:AC4', "", cell_format)
            worksheet.write_string('AC3', 'Não Sujeito a Segurança Social?', cell_format)
            worksheet.set_column('AC3:AC3', 35)  # Column Widths
            worksheet.merge_range('AD3:AD4', "", cell_format)
            worksheet.write_string('AD3', 'Contribuição Segurança Social', cell_format)
            worksheet.set_column('AD3:AD3', 35)  # Column Widths
            worksheet.merge_range('AE3:AE4', "", cell_format)
            worksheet.write_string('AE3', 'Base Tributável IRT', cell_format)
            worksheet.set_column('AE3:AE3', 25)  # Column Widths
            worksheet.merge_range('AF3:AF4', "", cell_format)
            worksheet.write_string('AF3', 'Isento IRT?', cell_format)
            worksheet.set_column('AF3:AF3', 15)  # Column Widths
            worksheet.merge_range('AG3:AG4', "", cell_format)
            worksheet.write_string('AG3', 'IRT Apurado', cell_format)
            worksheet.set_column('AG3:AG3', 15)  # Column Widths

            # Payslip Values
            xlsx_values = get_xlsx_dict_values(docs)
            index = 5 + len(xlsx_values)  # -d hr_payroll
            # Payslip Values
            for dic_value in xlsx_values:
                for key, value in dic_value.items():
                    # extract numbers from string
                    from_key = ''.join(map(str, [int(s) for s in [*key] if s.isdigit()]))
                    if 'M' in key:
                        worksheet.data_validation(key, {'validate': 'list', 'source': ['S', 'N']})
                    elif 'Z' in key:
                        formula1 = "{" + f'=+F{from_key}+G{from_key}+I{from_key}+V{from_key}+L{from_key}+H{from_key}+R{from_key}+Y{from_key}+X{from_key}' + "}"
                        worksheet.write_formula(key, formula1)
                    elif 'AA' in key:
                        worksheet.data_validation(key, {'validate': 'list', 'source': ['S', 'N']})
                    elif 'AB' in key:
                        formula2 = "{" + f'=+Z{from_key}-R{from_key}' + "}"
                        worksheet.write_formula(key, formula2)
                    elif 'AC' in key:
                        worksheet.data_validation(key, {'validate': 'list', 'source': ['S', 'N']})
                    elif 'AD' in key:
                        formula3 = "{" + f'=+AB{from_key}*0.03' + "}"
                        worksheet.write_formula(key, formula3)
                    elif 'AE' in key:
                        formula4 = "{" + f'=+AB{from_key}-AD{from_key}-J{from_key}-I{from_key}-H{from_key}' + "}"
                        worksheet.write_formula(key, formula4)
                    elif 'AF' in key:
                        worksheet.data_validation(key, {'validate': 'list', 'source': ['S', 'N']})
                    else:
                        worksheet.write(key, value)

            # # Calculate the total social security and IRT Calculated
            # formula5 = "{" + f'=SUM(AD5,AD{index})' + "}"
            # formula6 = "{" + f'=SUM(AG5,AG{index})' + "}"
            # worksheet.write_formula(f'AD{index}', formula5)
            # worksheet.write_formula(F'AG{index}', formula6)

            workbook.close()

            return new_dir_path

        def create_xml_file(remuneration_map_dict):
            remuneration_map_xml = dicttoxml(remuneration_map_dict, root=False, attr_type=False, fold_list=False)
            dom = parseString(remuneration_map_xml)
            data = dom.toprettyxml().replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8" ?>')

            return data

        def create_temp_xml_file(xml_data):
            temp_file = tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix=".xml")
            dir_path = temp_file.name
            file = temp_file.name.split('/')
            file[-1] = f"REMUNERATION_MAP_PERIOD_{period}.xml"
            new_dir_path = '/'.join(map(str, file))
            os.rename(dir_path, new_dir_path)
            temp_file.write(xml_data.encode("utf-8"))
            temp_file.seek(0)
            file = base64.b64encode(open(new_dir_path).read().encode("utf-8"))

            return new_dir_path

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        period = '%d-%s' % (period_date.year, months[period_date.month])

        if report_file == 'xml':
            remuneration_map_dict = create_remuneration_dict(period, docs)
            xml_data = create_xml_file(remuneration_map_dict)
            dir_path_file = create_temp_xml_file(xml_data)
        elif report_file == 'xlsx':
            dir_path_file = create_temp_xlsx_file(period, docs)
        else:
            return {}

        file_result = base64.b64encode(open(f'{dir_path_file}', 'rb').read())
        url_file = f'{base_url}/remuneration/map/download?dir_path_file={dir_path_file}'
        return url_file
