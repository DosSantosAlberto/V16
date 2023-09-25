from odoo import models, fields, api, _


class AgtModel2(models.TransientModel):
    _name = 'fiscal.reports.agt.model2'
    _description = 'Report Model 2 industrial tax'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        comodel_name="res.company", default=lambda self: self.env.user.company_id, string="Company")
    year_end = fields.Many2one(comodel_name='account.fiscal.year',
                               related='company_id.accounting_year', string="Ano Fiscal ")

    def get_data_account(self, code):
        rec = self.env['account.move.line'].search(
            [('account_id.code', 'ilike', code), ('move_id.year', '=', self.year_start.id),
             ('move_id.state', '=', 'posted')])
        credit = set([re.credit for re in rec])
        debit = set([re.debit for re in rec])
        return sum(credit) - sum(debit)

    def get_data_account_end(self, code):
        print('Ano Fiscal Atual')
        rec = self.env['account.move.line'].search(
            [('account_id.code', 'ilike', code), ('move_id.year', '=', self.year_end.id),
             ('move_id.state', '=', 'posted')])

        credit = set([re.credit for re in rec])
        debit = set([re.debit for re in rec])
        return sum(credit) - sum(debit)

    #def get_data_account_tax_end(self,amount):

       # print('###############################')
        #tax = self.env['account.tax'].search(
            #[('account_id.amount', 'ilike',amount)])
       # print("#############################################################################",tax)

    def print_report(self):
        return self.env.ref("es_account_report_ao.action_report_model2_ao").report_action(self)


"""
    def get_account_balance(self, code):
        previous_year = self.env['account.fiscal.year'].search([
            ('name', '=', str(int(self.year.name) - 1)),
            ('company_id', '=', self.company_id.id)
        ])

        current = sum(account.balance for account in self.env['account.move.line'].search(
            [
                ('account_id.code', '=like', '{}%'.format(code)),
                ('move_id.year', '=', self.year.id),
                ('move_id.state', '=', 'posted')
            ]
        ))

        previous = 0 if previous_year else sum(account.balance for account in self.env['account.move.line'].search(
            [
                ('account_id.code', '=like', '{}%'.format(code)),
                ('move_id.year', '=', previous_year.id),
                ('move_id.state', '=', 'posted')
            ]
        ))
        return {
            'current': current,
            'previous': previous
        }
"""
