from odoo import fields, models, api, _
from odoo.exceptions import Warning, ValidationError, UserError
from odoo.tools import safe_eval
from odoo.tools.misc import formatLang

from collections import defaultdict


class AccountMove(models.Model):
    _inherit = "account.move"
    _order = "id desc"

    def _default_fiscal_year(self):
        company_id = self.env.user.company_id
        return company_id.accounting_year.id

    def _default_fiscal_period(self):

        company_id = self.env.user.company_id
        for period in company_id.accounting_year.periods:
            if period.period == '12':
                return period.id
        return 0

    year = fields.Many2one(comodel_name='account.fiscal.year', default=lambda l: l._default_fiscal_year())
    period = fields.Many2one(comodel_name="account.fiscal.period", default=lambda l: l._default_fiscal_period())
    payment_difference = fields.Float("Payment Difference")
    cost_center = fields.Many2one(comodel_name="account.cost.center", string="Cost Center")
    has_cost_center = fields.Boolean(related='company_id.invoice_cost_center')

    def _prepare_cost_center(self):
        for res in self:
            if res.cost_center:
                for line in res.sudo().line_ids:
                    line.account_id.has_cost_center = True

    @api.constrains('date', 'invoice_date', 'year')
    def validate_date(self):
        for res in self:
            if res.company_id.accounting_year and res.year:
                if res.company_id.accounting_year == res.year:

                    if not (res.period.start_date <= res.date <= res.period.end_date):
                        raise ValidationError(_("A data %s esta fora do periodo %s \n "
                                                "Inicio: %s - Fim: %s\n Verificar por favor")
                                              % (res.date, res.period.name, res.period.start_date,
                                                 res.period.end_date))
                else:
                    raise ValidationError(_("Ano do registo corrente diferente do Ano fiscal da empresa"))

    @api.constrains('cost_center')
    def _check_cost_center(self):
        self._prepare_cost_center()

    @api.onchange('year')
    def onchange_year(self):
        for period in self.year.periods:
            if not self.period and period.period == 12:
                self.period = period

    @staticmethod
    def _set_format_sequence_agt(move, date_group):
        if move.move_type in ['in_invoice', 'out_invoice', 'out_refund', 'in_refund']:
            date_group['format_values']['seq_length'] = 1
            date_group['format'] = '{prefix1}{year:0{year_length}d}{prefix2}{seq:0{seq_length}d}{suffix}'

    @staticmethod
    def _set_prefix_sequence_agt(move, date_group):
        if move.move_type == 'out_invoice':
            date_group['format_values']['prefix1'] = "FT C"
        if move.move_type == 'in_invoice':
            date_group['format_values']['prefix1'] = "FT F"
        elif move.move_type == 'out_refund':
            date_group['format_values']['prefix1'] = "NC C"
        elif move.move_type == 'in_refund':
            date_group['format_values']['prefix1'] = "NC F"

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        def journal_key(move):
            return (move.journal_id, move.journal_id.refund_sequence and move.move_type)

        def date_key(move):
            return (move.date.year, move.date.month)

        grouped = defaultdict(  # key: journal_id, move_type
            lambda: defaultdict(  # key: first adjacent (date.year, date.month)
                lambda: {
                    'records': self.env['account.move'],
                    'format': False,
                    'format_values': False,
                    'reset': False
                }
            )
        )
        self = self.sorted(lambda m: (m.date, m.ref or '', m.id))
        highest_name = self[0]._get_last_sequence() if self else False

        # Group the moves by journal and month
        for move in self:
            if not highest_name and move == self[0] and not move.posted_before and move.date:
                # In the form view, we need to compute a default sequence so that the user can edit
                # it. We only check the first move as an approximation (enough for new in form view)
                pass
            elif (move.name and move.name != '/') or move.state != 'posted':
                try:
                    if not move.posted_before:
                        move._constrains_date_sequence()
                    # Has already a name or is not posted, we don't add to a batch
                    continue
                except ValidationError:
                    # Has never been posted and the name doesn't match the date: recompute it
                    pass
            group = grouped[journal_key(move)][date_key(move)]
            if not group['records']:
                # Compute all the values needed to sequence this whole group
                move._set_next_sequence()
                group['format'], group['format_values'] = move._get_sequence_format_param(move.name)
                group['reset'] = move._deduce_sequence_number_reset(move.name)
            group['records'] += move

        # Fusion the groups depending on the sequence reset and the format used because `seq` is
        # the same counter for multiple groups that might be spread in multiple months.
        final_batches = []
        for journal_group in grouped.values():
            journal_group_changed = True
            for date_group in journal_group.values():
                """set format and prefix sequence based AGT - @author: Hermenegildo Mulonga / Halow Tecnology """
                move._set_format_sequence_agt(move, date_group)
                move._set_prefix_sequence_agt(move, date_group)
                if (
                        journal_group_changed
                        or final_batches[-1]['format'] != date_group['format']
                        or dict(final_batches[-1]['format_values'], seq=0) != dict(date_group['format_values'], seq=0)
                ):
                    final_batches += [date_group]
                    journal_group_changed = False
                elif date_group['reset'] == 'never':
                    final_batches[-1]['records'] += date_group['records']
                elif (
                        date_group['reset'] == 'year'
                        and final_batches[-1]['records'][0].date.year == date_group['records'][0].date.year
                ):
                    final_batches[-1]['records'] += date_group['records']
                else:
                    final_batches += [date_group]

        # Give the name based on previously computed values
        for batch in final_batches:
            for move in batch['records']:
                move.name = batch['format'].format(**batch['format_values'])
                batch['format_values']['seq'] += 1
            batch['records']._compute_split_sequence()

        self.filtered(lambda m: not m.name).name = '/'

    def get_tax_line_details(self):
        """return: data for all taxes - @author: Hermenegildo Mulonga """
        tax_lines_data = []
        for line in self.invoice_line_ids:
            for tax_line in line.tax_ids:
                tax_lines_data.append({
                    'tax_exigibility': tax_line.tax_exigibility,
                    'tax_amount': line.price_subtotal * (tax_line.amount / 100),
                    'base_amount': line.price_subtotal,
                    'tax': tax_line,
                })
        return tax_lines_data

    def tax_of_invoice(self):
        taxes = []
        for line in self.invoice_line_ids:
            for tax in line.tax_ids:
                taxes.append(tax)
        return list(set(taxes))

    def amount_format(self, amount):
        return formatLang(self.env, amount)

    @api.constrains('journal_id')
    def _check_line_movement(self):
        for line in self.line_ids:
            if line.period.period in ['12', '0', '14', '13'] and line.account_id.nature != 'M':
                raise UserError(_("Apenas contas de movimentos podem ser "
                                  "lancadas no período ordinário.\n"
                                  "Rever a conta %s-%s" % (line.account_id.code, line.account_id.name)))

    def found_moviment(self, cod1, cod2):
        line_2 = self.env['account.move.line'].search(
            [
                ('move_id', '=', self.id),
                ('move_id.year.date_from', '>=', self.year.date_from),
                ('move_id.year.date_to', '<=', self.year.date_to),
                ('account_code', '=', str(cod2)),
                ('account_id.code', 'not like',
                 '{}9%'.format(cod2)),
                ('balance', '!=', '0'),
                ('company_id', '=', self.company_id.id),
            ], order='account_code'
        )
        line_1 = self.env['account.move.line'].search(
            [
                ('move_id', '=', self.id),
                ('move_id.year.date_from', '>=', self.year.date_from),
                ('move_id.year.date_to', '<=', self.year.date_to),
                ('account_code', '=', str(cod1)),
                ('account_id.code', 'not like',
                 '{}9%'.format(cod1)),
                ('balance', '!=', '0'),
                ('company_id', '=', self.company_id.id),
            ], order='account_code'
        )
        balance1, balance2 = abs(sum([re.balance for re in line_1])), abs(sum([re.balance for re in line_2]))
        balance = balance1 - balance2
        return balance

    def sum_reason_start_digit_two(self, date_to, date_from):
        balance = self.make_clearance_classe_6(date_to, date_from)[0] + \
                  self.make_clearance_classe_7(date_to, date_from)[0]
        print("TUdo esta muito confuso", balance)
        account = self.env['account.account'].search(
            [('code', '=', '8219'), ('company_id', '=', self.company_id.id), ], limit=1)
        if account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(balance) if balance > 0 else 0.0,
                'debit': abs(balance) if balance < 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)

        else:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('8219')))
        account = self.env['account.account'].search(
            [('code', '=', '839'), ('company_id', '=', self.company_id.id), ], limit=1)
        valor = self.found_moviment('831', '832')
        if valor != 0.0 and account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(valor) if valor < 0 else 0.0,
                'debit': abs(valor) if valor > 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)

        elif not account:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('839')))
        account = self.env['account.account'].search(
            [('code', '=', '882'), ('company_id', '=', self.company_id.id), ], limit=1)

        valor = self.found_moviment('831', '832')
        if valor != 0.0 and account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(valor) if valor > 0 else 0.0,
                'debit': abs(valor) if valor < 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)


        elif not account:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('882')))

        account = self.env['account.account'].search(
            [('code', '=', '849'), ('company_id', '=', self.company_id.id), ], limit=1)

        valor = self.found_moviment('841', '842')
        if valor != 0.0 and account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(valor) if valor < 0 else 0.0,
                'debit': abs(valor) if valor > 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)


        elif not account:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('849')))
        account = self.env['account.account'].search(
            [('code', '=', '859'), ('company_id', '=', self.company_id.id), ], limit=1)
        valor = self.found_moviment('851', '852')
        if valor != 0.0 and account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(valor) if valor < 0 else 0.0,
                'debit': abs(valor) if valor > 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)

        elif not account:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('859')))
        account = self.env['account.account'].search(
            [('code', '=', '884'), ('company_id', '=', self.company_id.id), ], limit=1)
        valor = self.found_moviment('851', '852')
        if valor != 0.0 and account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(valor) if valor > 0 else 0.0,
                'debit': abs(valor) if valor < 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)

        elif not account:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('884')))

        account = self.env['account.account'].search(
            [('code', '=', '869'), ('company_id', '=', self.company_id.id), ], limit=1)

        valor = self.found_moviment('861', '862')
        if valor != 0.0 and account:
            print(account.code, 'O probelma de tudo')
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(valor) if valor < 0 else 0.0,
                'debit': abs(valor) if valor > 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)
            account = self.env['account.account'].search(
                [('code', '=', '881'), ('company_id', '=', self.company_id.id), ], limit=1)


        elif not account:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('869')))

        if account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(balance) if balance < 0 else 0.0,
                'debit': abs(balance) if balance > 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)


        else:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('881')))

        account = self.env['account.account'].search(
            [('code', '=', '881'), ('company_id', '=', self.company_id.id), ], limit=1)
        move = self.env['account.move.line'].create({
            'move_id': self.id,
            'account_id': account.id,
            'credit': abs(balance) * 0.25 if balance > 0 else 0.0,
            'debit': abs(balance) * 0.25 if balance < 0 else 0.0
        })
        print(move.credit, "--------------", move.debit)

        account = self.env['account.account'].search(
            [('code', '=', '879')], limit=1)
        if account:
            print(account.code)

            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(balance) * 0.25 if balance < 0 else 0.0,
                'debit': abs(balance) * 0.25 if balance > 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)


        else:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('879')))

        account = self.env['account.account'].search(
            [('code', '=', '341'), ('company_id', '=', self.company_id.id), ], limit=1)
        if account:
            print(account.code)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(balance) * 0.25 if balance < 0 else 0.0,
                'debit': abs(balance) * 0.25 if balance > 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)


        else:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('341')))
        account = self.env['account.account'].search(
            [('code', '=', '879'), ('company_id', '=', self.company_id.id), ], limit=1)
        if account:
            print(account.code)

            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(balance) * 0.25 if balance > 0 else 0.0,
                'debit': abs(balance) * 0.25 if balance < 0 else 0.0
            })
            print(move.credit, "--------------", move.debit)


        else:
            raise ValidationError('A conta com {} não foi encontrada\n'
                                  ''
                                  'Por favor contactar o contabilista para a criação da conta'.format(
                ('879')))

    def make_clearance_classe_6(self, date_to, date_from):
        """Apuramento do iva  - @author: Inocencio Chipoia / CBS Compllexus """
        reason_six = ['61', '62', '63', '64', '65', '66', '67', '68', '69']
        balance_digit_two = 0.0
        sum_tree = 0.0
        sum_4 = 0.0
        sum_5 = 0.0
        sum_6 = 0.0
        i = 1

        for rec in reason_six:
            lines = self.env['account.move.line'].search(
                [
                    ('move_id.state', '=', 'posted'),
                    ('move_id.year.date_from', '>=', self.year.date_from),
                    ('move_id.year.date_to', '<=', self.year.date_to),
                    ('reason_code', '=', rec),
                    ('account_id.code', 'not like',
                     '{}9%'.format(rec)),
                    ('balance', '!=', '0'),
                    ('company_id', '=', self.company_id.id),
                ], order='account_code'
            )
            balance = (
                sum([abs(re.balance) for re in lines]))
            cods = set()
            for re in lines:
                cods.add(re.account_id.code)
            for c in cods:
                account = self.env['account.account'].search(
                    [('code', '=', c[:2] + '9')], limit=1)
                if account:
                    print(account.code)

                    move = self.env['account.move.line'].create({
                        'move_id': self.id,
                        'account_id': account.id,
                        'credit': abs(balance) if balance > 0 else 0.0,
                        'debit': abs(balance) if balance < 0 else 0.0
                    })
                else:
                    raise ValidationError('A conta com {} não foi encontrada\n'
                                          ''
                                          'Por favor contactar o contabilista para a criação da conta'.format(
                        (c[:2] + "9")))

                if int(c[1:2]) < 6:
                    account = self.env['account.account'].search(
                        [('code', '=', '82' + c[1:2])], limit=1)
                    if account:
                        move = self.env['account.move.line'].create({
                            'move_id': self.id,
                            'account_id': account.id,
                            'credit': abs(balance) if balance < 0 else 0.0,
                            'debit': abs(balance) if balance > 0 else 0.0
                        })
                    else:
                        raise ValidationError('A conta com {} não foi encontrada\n'
                                              ''
                                              'Por favor contactar o contabilista para a criação da conta'.format(
                            ("82" + c[:2])))
                    balance_digit_two += balance

                elif int(c[1:2]) == 6:
                    account = self.env['account.account'].search(
                        [('code', '=', '831'), ('company_id', '=', self.company_id.id), ], limit=1)
                    if account:
                        move = self.env['account.move.line'].create({
                            'move_id': self.id,
                            'account_id': account.id,
                            'credit': abs(balance) if balance < 0 else 0.0,
                            'debit': abs(balance) if balance > 0 else 0.0
                        })
                    else:
                        raise ValidationError('A conta com {} não foi encontrada\n'
                                              ''
                                              'Por favor contactar o contabilista para a criação da conta'.format(
                            ("831")))

                elif int(c[1:2]) == 7:
                    account = self.env['account.account'].search(
                        [('code', '=', '841'), ('company_id', '=', self.company_id.id), ], limit=1)
                    if account:
                        move = self.env['account.move.line'].create({
                            'move_id': self.id,
                            'account_id': account.id,
                            'credit': abs(balance) if balance < 0 else 0.0,
                            'debit': abs(balance) if balance > 0 else 0.0
                        })
                    else:
                        raise ValidationError('A conta com {} não foi encontrada\n'
                                              ''
                                              'Por favor contactar o contabilista para a criação da conta'.format(
                            ("841")))

                elif int(c[1:2]) == 8:
                    account = self.env['account.account'].search(
                        [('code', '=', '851'), ('company_id', '=', self.company_id.id), ], limit=1)
                    if account:
                        move = self.env['account.move.line'].create({
                            'move_id': self.id,
                            'account_id': account.id,
                            'credit': abs(balance) if balance < 0 else 0.0,
                            'debit': abs(balance) if balance > 0 else 0.0
                        })
                    else:
                        raise ValidationError('A conta com {} não foi encontrada\n'
                                              ''
                                              'Por favor contactar o contabilista para a criação da conta'.format(
                            ("831")))

                elif int(c[1:2]) == 9:
                    account = self.env['account.account'].search(
                        [('code', '=', '861'), ('company_id', '=', self.company_id.id), ], limit=1)
                    if account:
                        move = self.env['account.move.line'].create({
                            'move_id': self.id,
                            'account_id': account.id,
                            'credit': abs(balance) if balance < 0 else 0.0,
                            'debit': abs(balance) if balance > 0 else 0.0
                        })
                    else:
                        raise ValidationError('A conta com {} não foi encontrada\n'
                                              ''
                                              'Por favor contactar o contabilista para a criação da conta'.format(
                            ("861")))

                break
        return balance_digit_two, sum_tree, sum_4, sum_5, sum_6

    def make_clearance_classe_7(self, date_to, date_from):
        """Apuramento do iva  - @author: Inocencio Chipoia / CBS Compllexus """
        reason_seven = ['71', '72', '73', '75', '76', '77', '78', '79']
        balance_digit_two = 0.0
        sum_two_debit = 0.0
        sum_4 = 0.0
        sum_5 = 0.0
        sum_6 = 0.0
        sum_9 = 0.0
        i = 6
        j = 4
        for rec in reason_seven:
            lines = self.env['account.move.line'].search(
                [
                    ('move_id.state', '=', 'posted'),
                    ('move_id.year.date_from', '>=', self.year.date_from),
                    ('move_id.year.date_to', '<=', self.year.date_to),
                    ('reason_code', '=', rec),
                    ('account_id.code', 'not like',
                     '{}9%'.format(rec)),
                    ('balance', '!=', '0'),
                    ('company_id', '=', self.company_id.id),
                ], order='account_code'
            )
            cods = set()
            for re in lines:
                cods.add(re.account_id.code)
            balance = (
                sum([abs(re.balance) for re in lines]))
            for c in cods:
                account = self.env['account.account'].search(
                    [('code', '=', c[:2] + '9')], limit=1)
                if account:
                    move = self.env['account.move.line'].create({
                        'move_id': self.id,
                        'account_id': account.id,
                        'credit': abs(balance) if balance > 0 else 0.0,
                        'debit': abs(balance) if balance < 0 else 0.0
                    })
                else:
                    raise ValidationError('A conta com {} não foi encontrada\n'
                                          ''
                                          'Por favor contactar o contabilista para a criação da conta'.format(
                        c[:2] + '9'))

                if int(c[1:2]) < 6:
                    if i != 4 and rec == '71':
                        account = self.env['account.account'].search(
                            [('code', '=', '826'), ('company_id', '=', self.company_id.id), ], limit=1)
                        if account:
                            move = self.env['account.move.line'].create({
                                'move_id': self.id,
                                'account_id': account.id,
                                'credit': abs(balance) if balance < 0 else 0.0,
                                'debit': abs(balance) if balance > 0 else 0.0
                            })
                            balance_digit_two += balance
                        else:
                            raise ValidationError('A conta com {} não foi encontrada\n'
                                                  ''
                                                  'Por favor contactar o contabilista para a criação da conta'.format(
                                '829'))

                    if i != 4 and rec == '72':
                        account = self.env['account.account'].search(
                            [('code', '=', '827'), ('company_id', '=', self.company_id.id), ], limit=1)
                        if account:
                            move = self.env['account.move.line'].create({
                                'move_id': self.id,
                                'account_id': account.id,
                                'credit': abs(balance) if balance < 0 else 0.0,
                                'debit': abs(balance) if balance > 0 else 0.0
                            })
                            balance_digit_two += balance
                        else:
                            raise ValidationError('A conta com {} não foi encontrada\n'
                                                  ''
                                                  'Por favor contactar o contabilista para a criação da conta'.format(
                                '827'))
                    if i != 4 and rec == '73':
                        account = self.env['account.account'].search(
                            [('code', '=', '828'), ('company_id', '=', self.company_id.id), ], limit=1)
                        if account:
                            move = self.env['account.move.line'].create({
                                'move_id': self.id,
                                'account_id': account.id,
                                'credit': abs(balance) if balance < 0 else 0.0,
                                'debit': abs(balance) if balance > 0 else 0.0
                            })
                            balance_digit_two += balance
                        else:
                            raise ValidationError('A conta com {} não foi encontrada\n'
                                                  ''
                                                  'Por favor contactar o contabilista para a criação da conta'.format(
                                '828'))
                    if i != 4 and rec == '75':
                        account = self.env['account.account'].search(
                            [('code', '=', '829'), ('company_id', '=', self.company_id.id), ], limit=1)
                        if account:
                            move = self.env['account.move.line'].create({
                                'move_id': self.id,
                                'account_id': account.id,
                                'credit': abs(balance) if balance < 0 else 0.0,
                                'debit': abs(balance) if balance > 0 else 0.0
                            })
                            balance_digit_two += balance
                        else:
                            raise ValidationError('A conta com {} não foi encontrada\n'
                                                  ''
                                                  'Por favor contactar o contabilista para a criação da conta'.format(
                                '829'))
                    i += 1
                elif int(c[1:2]) == 6:
                    account = self.env['account.account'].search(
                        [('code', '=', '832'), ('company_id', '=', self.company_id.id), ], limit=1)
                    if account:
                        move = self.env['account.move.line'].create({
                            'move_id': self.id,
                            'account_id': account.id,
                            'credit': abs(balance) if balance < 0 else 0.0,
                            'debit': abs(balance) if balance > 0 else 0.0
                        })
                    else:
                        raise ValidationError('A conta com {} não foi encontrada\n'
                                              ''
                                              'Por favor contactar o contabilista para a criação da conta'.format(
                            '832'))
                elif int(c[1:2]) > 6:
                    if j == 4:
                        sum_5 = abs(balance)
                    elif j == 5:
                        sum_6 = abs(balance)
                    else:
                        sum_9 = abs(balance)
                    account = self.env['account.account'].search(
                        [('code', '=', '8' + str(j - 1) + '2'), ('company_id', '=', self.company_id.id), ], limit=1)
                    if account:
                        move = self.env['account.move.line'].create({
                            'move_id': self.id,
                            'account_id': account.id,
                            'credit': abs(balance) if balance < 0 else 0.0,
                            'debit': abs(balance) if balance > 0 else 0.0
                        })
                    else:
                        raise ValidationError('A conta com {} não foi encontrada\n'
                                              ''
                                              'Por favor contactar o contabilista para a criação da conta'.format(
                            '8' + str(j - 1) + '2'))

                j += 1
                break
        return balance_digit_two, sum_4, sum_5, sum_6, sum_9

    def make_clearance(self, date_to, date_from):
        """Apuramento do iva  - @author: Inocencio Chipoia / CBS Compllexus """
        self = self.with_context({'check_move_validity': False})
        self.sum_reason_start_digit_two(date_to, date_from)
        # self.make_clearance_classe_7(date_to, date_from)

    def amount_balance(self, code, date_to, date_from):
        account = self.env['account.account'].search(
            [('code', '=', code), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        move_line = self.env['account.move.line'].search(
            [
                ('move_id.state', '=', 'posted'),
                ('move_id.date', '>=', date_from),
                ('move_id.date', '<=', date_to),
                ('account_code', '=', code),
                ('balance', '!=', '0'),
                ('company_id', '=', self.company_id.id),
            ]
        )
        balance = sum((abs(rec.balance) for rec in move_line))
        return balance

    def create_account_move(self, code, date_to, date_from):
        balance = 0.0
        account = self.env['account.account'].search(
            [('code', '=', code)], limit=1)
        move_line = self.env['account.move.line'].search(
            [
                ('move_id.state', '=', 'posted'),
                ('move_id.date', '>=', date_from),
                ('move_id.date', '<=', date_to),
                ('account_code', '=', code),
                ('balance', '!=', '0'),
                ('company_id', '=', self.company_id.id),
            ]
        )
        credit, debit = sum([rec.credit for rec in move_line]), sum([rec.debit for rec in move_line])
        move = self.env['account.move.line'].create({
            'move_id': self.id,
            'account_id': account.id,
            'credit': credit,
            'debit': debit
        })
        balance = (credit - debit)
        return move, balance

    def make_iva_clerance(self, date_to, date_from):
        """Apuramento do iva  - @author: Inocencio Chipoia / CBS Compllexus """
        balance = []
        self = self.with_context({
            'check_move_validity': False})
        list_iva_suportado = ('34511', '34512', '34513')
        list_iva_dedutivel = ('34521', '34522', '34523')
        iva_liquidado = '34531'
        iva_apurado = '34551'
        iva_apagar = '34561'
        for a in list_iva_suportado:
            balance.append(self.create_account_move(a, date_to, date_from)[1])
        for b in list_iva_dedutivel:
            balance.append(self.create_account_move(b, date_to, date_from)[1])
        amount = sum(balance)
        if amount > 0:
            account = self.env['account.account'].search(
                [('code', '=', iva_liquidado), ('company_id', '=', self.company_id.id), ], limit=1)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': 0.0,
                'debit': abs(amount)
            })
            account = self.env['account.account'].search(
                [('code', '=', iva_apurado), ('company_id', '=', self.company_id.id), ], limit=1)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(amount),
                'debit': 0.0
            })
            account = self.env['account.account'].search(
                [('code', '=', iva_apagar), ('company_id', '=', self.company_id.id), ], limit=1)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': 0.0,
                'debit': abs(amount),
            })
        else:
            account = self.env['account.account'].search(
                [('code', '=', iva_liquidado), ('company_id', '=', self.company_id.id), ], limit=1)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'debit': 0.0,
                'credit': abs(amount),

            })
            account = self.env['account.account'].search(
                [('code', '=', iva_apurado), ('company_id', '=', self.company_id.id), ], limit=1)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': 0.0,
                'debit': abs(amount),
            })
            account = self.env['account.account'].search(
                [('code', '=', iva_apagar), ('company_id', '=', self.company_id.id), ], limit=1)
            move = self.env['account.move.line'].create({
                'move_id': self.id,
                'account_id': account.id,
                'credit': abs(amount),
                'debit': 0.0
            })

    class AccountMoveLine(models.Model):
        _inherit = 'account.move.line'
        _order = "id asc"
        cash_flow = fields.Many2one(string="Cash Flow", related='account_id.cash_flow', store=True)
        iva_plan = fields.Many2one(string="Plan IVA", related='account_id.iva_plan', store=True)
        fiscal_plan = fields.Many2one(string="Plan Fiscal", related='account_id.fiscal_plan', store=True)
        has_cost_center = fields.Boolean(related='account_id.has_cost_center')
        has_cash_flow = fields.Boolean(related='account_id.has_cash_flow')
        has_iva = fields.Boolean(related='account_id.has_iva')
        has_fiscal_plan = fields.Boolean(related='account_id.has_fiscal_plan')
        move_id_state = fields.Selection(related='move_id.state', string="state")
        period = fields.Many2one(comodel_name="account.fiscal.period", compute='_store_period', store=True)
        cost_center = fields.Many2one(comodel_name="account.cost.center", related='move_id.cost_center',
                                      string="Cost Center", store=True)

        @api.depends('move_id')
        def _store_period(self):
            for res in self:
                if res.move_id.period:
                    res.period = res.move_id.period
