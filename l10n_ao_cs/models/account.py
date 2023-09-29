from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    reason_code = fields.Char(string="Reason")
    integrator_code = fields.Char(string="Integrator")
    nature = fields.Selection([
        ('C', 'Class'),
        ('R', 'Reason'),
        ('I', 'Integrator'),
        ('M', 'Movement'),
    ], string="Nature")

    @api.constrains('code')
    def _check_account_code(self):
        size = len(self.code)
        _code = self.code.replace('.', '')
        if size == 3:
            domain = [('code', '=', _code[:-1])]
            if self.env.user.has_group('base.group_multi_company'):
                domain.append(('company_id', '=', self.company_id.id))
            if not self.env['account.account'].search(domain):
                raise UserError(_("Invalid Account.\n"
                                  "Not exist reason to this account %s Consult the accountant." % _code))
        elif size >= 4:
            if _code.count('0') != 0:
                _code = _code[:_code.find('0')]
            domain = [('code', '=', _code[:-1])]
            if self.env.user.has_group('base.group_multi_company'):
                domain.extend([('company_id', '=', self.company_id.id)])
            account = self.env['account.account'].search(domain)
            if not account and self.company_id.control_account_nature:
                raise UserError(_("Create Integrated Account %s\nNeed create integrator account first") % _code[:-1])

    def check_nature(self, res_id):
        size = len(res_id.code)
        _code = res_id.code.replace('.', '')
        if _code:
            if size == 1:
                res_id.nature = 'C'
            elif size == 2:
                res_id.nature = 'R'
            elif size == 3:
                res_id.nature = 'I'
                res_id.reason_code = res_id.get_reason_code(_code)
            elif size >= 4:
                if _code.count('0') != 0:
                    _code = _code[:_code.find('0')]
                domain = [('code', '=', _code[:-1])]
                if self.env.user.has_group('base.group_multi_company'):
                    domain.append(('company_id', '=', res_id.company_id.id))
                account = self.env['account.account'].search(domain)
                # type_receivable = self.env.ref('account.data_account_type_receivable')
                # type_payable = self.env.ref('account.data_account_type_payable')
                if account:
                    account.nature = 'I'
                    res_id.nature = 'M'
                    res_id.reason_code = res_id.get_reason_code(_code)
                    res_id.integrator_code = _code[:-1]
                else:
                    if res_id.company_id.control_account_nature:
                        # CREATE ACCOUNT, Getting the order of accountants right
                        # allow = False
                        # if res_id.account_type.id in [type_payable.id, type_receivable.id]:
                        #     allow = True
                        # self.env['account.account'].create({
                        #     'code': _code[:-1],
                        #     'name': '.........................',
                        #     'account_type': res_id.account_type.id,
                        #     'reconcile': allow
                        # })
                        pass

    def _update_code_nature(self):
        for rec in self.search([()]):
            rec.check_nature(rec)

    def write(self, vals):
        if vals.get('code'):
            vals['code'] = vals['code'].replace(" ", "")
            for res in self:
                self.check_nature(res)
        return super(AccountAccount, self).write(vals)

    @api.model
    def create(self, vals):
        vals['code'] = str(vals['code']).replace(" ", "")
        result = super(AccountAccount, self).create(vals)
        self.check_nature(result)
        return result

    def get_reason_code(self, code):
        if self.env['account.account'].search([('code', '=', code[:2])]):
            return code[:2]
        return ''
