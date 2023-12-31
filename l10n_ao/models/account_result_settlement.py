from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class AccountResultSettlement(models.Model):
    _name = "account.result.settlement"
    _description = "Wizard to compute the result settlement"

    _accounts = ["61", "62", "63", "64", "65", "66", "67", "68", "69", "71", "72", "73", "75", "76", "77", "78",
                 "79"]
    _trans_accounts = ["619", "629", "639", "649", "659", "669", "679", "6819", "699", "719", "729", "739", "759",
                       "769", "779", "7819", "799"]
    _result_accounts = ["821", "822", "823", "824", "825", "831", "841", "851", "861", "826", "827", "828", "829",
                        "832", "842", "852", "862"]
    _settled_accounts = ["8219", "8219", "8219", "8219", "8219", "839", "849", "859", "869", "8219", "8219", "8219",
                         "8219", "839", "849", "859", "869"]
    _netresult_accounts = ["881", "881", "881", "881", "881", "882", "883", "884", "886", "881", "881", "881", "881",
                           "882", "883", "884", "886"]

    _settled_accounts_map = ["8219", "839", "849", "859", "869"]
    _netresult_accounts_map = ["881", "882", "883", "884", "886"]

    name = fields.Char(_('Document Ref'), default='New')
    date = fields.Date("Date", default=fields.Date.today())

    fiscal_year = fields.Integer("Fiscal Year", default=fields.Date.today().year)
    journal_id = fields.Many2one("account.journal", "Journal", required=True)
    date_start = fields.Date(string="From date", required=True, readonly=True, states={"draft": [("readonly", False)]})
    date_end = fields.Date(string="To date", required=True, readonly=True, states={"draft": [("readonly", False)]})
    check_draft_moves = fields.Boolean("Check Draft Moves")
    move_balance_id = fields.Many2one("account.move", string="Revenue and Expenses Move", readonly="1")
    move_pl_id = fields.Many2one("account.move", string="Profit & Loss Balance Move", readonly="1")
    move_result_id = fields.Many2one("account.move", string="Results Balance Move", readonly="1")
    move_netresult_id = fields.Many2one("account.move", string="Net Result Move", readonly="1")
    move_tax_id = fields.Many2one("account.move", string="Tax Settlement Move", readonly="1")
    tax_id = fields.Many2one("account.tax", string="Tax", required=True)
    move_balance_lines = fields.One2many(related="move_balance_id.line_ids", )
    move_balance_state = fields.Selection(related="move_balance_id.state", readonly="1")
    move_pl_lines = fields.One2many(related="move_pl_id.line_ids", )
    move_pl_state = fields.Selection(related="move_pl_id.state", readonly="1")
    move_result_lines = fields.One2many(related="move_result_id.line_ids", )
    move_result_state = fields.Selection(related="move_result_id.state", readonly="1")
    move_netresult_lines = fields.One2many(related="move_netresult_id.line_ids", )
    move_netresult_state = fields.Selection(related="move_netresult_id.state", readonly="1")
    move_tax_lines = fields.One2many(related="move_tax_id.line_ids", )
    move_tax_state = fields.Selection(related="move_tax_id.state", readonly="1")
    company_id = fields.Many2one('res.company', _('Company'), default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    communication = fields.Char(_('Communication'))
    net_result = fields.Float("Year Net Result")
    tax_result = fields.Float("Tax Result")
    net_result_signed = fields.Float("Year Net Result Signed")
    tax_result_signed = fields.Float("Tax Result Signed")
    state = fields.Selection([("draft", "Draft"), ('compute', 'Computed'), ("posted", "Posted"), ('cancel', 'Cancel')],
                             default="draft")

    def action_view_moves(self):
        # Return an action for showing moves
        ids = [self.move_balance_id.id, self.move_pl_id.id, self.move_result_id.id, self.move_netresult_id.id,
               self.move_tax_id.id]
        return {
            "name": _(f" {self.fiscal_year} Settlment Result Moves"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.move",
            "domain": [("id", "in", ids)],
        }

    @api.onchange("fiscal_year")
    def _onchange_year(self):
        self.date_start = datetime(self.fiscal_year, 1, 1)
        self.date_end = datetime(self.fiscal_year, 12, 31)

    def action_post(self):
        if self.move_balance_id:
            self.move_balance_id.post()
        if self.move_pl_id:
            self.move_pl_id.post()
        if self.move_result_id:
            self.move_result_id.post()
        if self.move_netresult_id:
            self.move_netresult_id.post()
        if self.move_tax_id:
            self.move_tax_id.post()

        if self.move_balance_id.state == "post" \
                and self.move_pl_id.state == "post" \
                and self.move_result_id.state == "post" \
                and self.move_netresult_id.state == "post" and self.move_tax_id.state == "post":
            self._check_existing_settlements()
            self.state = "post"

    def _check_existing_settlements(self):
        existing = self.search([("company_id", '=', self.company_id.id),
                                ("date_start", ">=", self.date_start),
                                ("date_end", "<=", self.date_end),
                                ("state", "=", "posted")])
        if existing:
            raise ValidationError(
                _(f"There is already a settlement for start date {self.date_start} to end date {self.date_end} posted."))

    def action_compute_result(self):
        if self.check_draft_moves:
            self.action_check_draft_moves()

        if not self.move_balance_id:
            self.create_balance_moves()
        if not self.move_pl_id:
            self.create_pl_moves()
        if not self.move_result_id:
            self.create_result_moves()
        if not self.move_netresult_id:
            self.create_netresult_moves()
        if not self.move_tax_id:
            self.create_tax_settlement()

        if self.move_balance_id.state and self.move_pl_id.state and self.move_result_id.state and \
                self.move_netresult_id.state and self.move_tax_id.state:
            self.state = "compute"

    def action_recompute_result(self):
        if self.move_balance_id:
            self.move_balance_id.unlink()
        if self.move_pl_id:
            self.move_pl_id.unlink()
        if self.move_result_id:
            self.move_result_id.unlink()
        if self.move_netresult_id:
            self.move_netresult_id.unlink()
        if self.move_tax_id:
            self.move_tax_id.unlink()
        self.action_compute_result()

    def action_cancel(self):
        if self.move_balance_id:
            self.move_balance_id.unlink()
        if self.move_pl_id:
            self.move_pl_id.unlink()
        if self.move_result_id:
            self.move_result_id.unlink()
        if self.move_netresult_id:
            self.move_netresult_id.unlink()
        if self.move_tax_id:
            self.move_tax_id.unlink()
        self.state = "cancel"

    def action_draft(self):
        self.state = "draft"

    def _get_account_balance(self, account_code, move_id=False, exception=[]):
        account_moves = self.env["account.move.line"]
        account_ids = self.env['account.account'].search([('code', '=like', account_code + "%"),
                                                          ("code", 'not in', exception),
                                                          ("company_id", "=", self.company_id.id),
                                                          ('deprecated', '=', False)]).mapped("id")

        if move_id:
            account_moves = self.env["account.move.line"].search([("account_id", 'in', account_ids),
                                                                  ("move_id", "=", move_id.id),
                                                                  # ("date", ">=", date_start), TODO: Perguntar ao José em relação as datas como deve ser
                                                                  # ("date", "<", date_end),
                                                                  ("company_id", "=", self.company_id.id)])
        else:
            account_moves = self.env["account.move.line"].search([("account_id", 'in', account_ids),
                                                                  ("date", ">=", self.date_start),
                                                                  ("date", "<", self.date_end),
                                                                  ("company_id", "=", self.company_id.id)])
        codes = account_moves.mapped("account_id.code")
        balances = account_moves.mapped("balance")
        result = sum(account_moves.mapped("balance"))
        return result

    def _get_double_move_line_vals(self, debit_account_id, credit_account_id, amount_currency, move_id):
        """ Returns values common to both move lines (except for debit, credit and amount_currency which are reversed)
        """
        debit_account = credit_account = self.env["account.account"]
        if amount_currency < 0:
            debit_account = debit_account_id
            credit_account = credit_account_id
        elif amount_currency > 0:
            debit_account = credit_account_id
            credit_account = debit_account_id

        return [{
            'account_id': debit_account.id,
            'move_id': move_id.id,
            'debit': abs(amount_currency),
            'credit': 0.0,
            'amount_currency': amount_currency if amount_currency > 0 else -1 * amount_currency,
        },
            {
                'account_id': credit_account.id,
                'move_id': move_id.id,
                'debit': 0.0,
                'credit': abs(amount_currency),
                'amount_currency': amount_currency if amount_currency < 0 else -1 * amount_currency,
            }
        ]

    def _get_move_vals(self):
        """
            Return dict to create the payment move
        """
        journal = self.journal_id
        # if not journal.sequence_id:
        #     raise UserError(_('Configuration Error !'),
        #                     _('The journal %s does not have a sequence, please specify one.') % journal.name)
        # if not journal.sequence_id.active:
        #     raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        # name = journal.with_context().sequence_id.next_by_id()
        return {
            # 'name': self.name,
            'date': datetime(self.fiscal_year, 12, 31),
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
            'transaction_type': 'A',
        }

    def create_balance_moves(self):
        move_vals = self._get_move_vals()
        move_vals["name"] = _(f"Settlement {self.fiscal_year} Balance")
        self.move_balance_id = self.env["account.move"].create(move_vals)
        aml_transport_list = []
        debit_account = credit_account = self.env["account.account"]
        # Sum all the balance from account 6X and 7X to 6X9 and 7X9
        for idx in range(len(self._accounts)):
            # balance = self._get_account_balance(self._accounts[idx])
            account_accounts = self.env["account.account"].search([("code", "=like", self._accounts[idx] + "%"),
                                                                   ("code", "!=", self._trans_accounts[idx]),
                                                                   ("company_id", "=", self.company_id.id),
                                                                   ('deprecated', '=', False)])
            transf_account = self.env["account.account"].search([("code", "=", self._trans_accounts[idx]),
                                                                 ("company_id", "=", self.company_id.id)])

            if not transf_account:
                raise ValidationError(f"There is no account chart {self._trans_accounts[idx]}!")

            for account in account_accounts:
                balance = self._get_account_balance(account.code, exception=self._trans_accounts)
                if not abs(balance):
                    continue
                aml_list = self._get_double_move_line_vals(account, transf_account, balance,
                                                           self.move_balance_id)
                for aml in aml_list:
                    self.env["account.move.line"].with_context(check_move_validity=False).create(aml)
                    # aml_transport_list.append(aml_id)

                # aml_transport_list.append(False)

    def create_pl_moves(self):
        move_vals = self._get_move_vals()
        move_vals["name"] = _(f"Settlement {self.fiscal_year} Profit & Loss")
        self.move_pl_id = self.env["account.move"].create(move_vals)
        # Transport all the amount from the transport account to the result accounts
        for idx in range(len(self._result_accounts)):
            balance = self._get_account_balance(self._trans_accounts[idx], self.move_balance_id)
            if balance == 0:
                continue
            res_account = self.env["account.account"].search([("code", "=", self._result_accounts[idx]),
                                                              ("company_id", "=", self.company_id.id)])
            transf_account = self.env["account.account"].search([("code", "=", self._trans_accounts[idx]),
                                                                 ("company_id", "=", self.company_id.id)])
            if not res_account:
                raise ValidationError(f"There is no account chart {self._trans_accounts[idx]}!")
            aml_list = self._get_double_move_line_vals(transf_account, res_account, balance, self.move_pl_id)
            for aml in aml_list:
                self.env["account.move.line"].with_context(check_move_validity=False).create(aml)

    def create_result_moves(self):
        move_vals = self._get_move_vals()
        move_vals["ref"] = _(f"Settlement {self.fiscal_year} Results")
        self.move_result_id = self.env["account.move"].create(move_vals)
        # Here we have the movement of each 821 -> 8219 that are result accounts to settled accounts
        for idx in range(len(self._result_accounts)):
            balance = self._get_account_balance(self._result_accounts[idx], self.move_pl_id)
            if balance == 0:
                continue
            result_account = self.env["account.account"].search([("code", "=", self._result_accounts[idx]),
                                                                 ("company_id", "=", self.company_id.id)])
            settled_account = self.env["account.account"].search([("code", "=", self._settled_accounts[idx]),
                                                                  ("company_id", "=", self.company_id.id)])

            if not settled_account:
                raise ValidationError(
                    _(f"It's missing account {self._settled_accounts[idx]} to compute the settlement result"))

            if not result_account:
                raise ValidationError(
                    _(f"It's missing account {self._result_accounts[idx]} to compute the settlement result"))

            aml_list = self._get_double_move_line_vals(result_account, settled_account, balance,
                                                       self.move_result_id)
            for aml in aml_list:
                self.env["account.move.line"].with_context(check_move_validity=False).create(aml)
            # settled_balances[self._settled_accounts[idx]] += balance

    def create_netresult_moves(self):
        # Here we transfer the balance from settled accounts map to final account mpa.
        move_vals = self._get_move_vals()
        move_vals["ref"] = _(f"Settlement {self.fiscal_year} Net Result")
        self.move_netresult_id = self.env["account.move"].create(move_vals)
        settled_balances = {"8219": 0, "839": 0, "849": 0, "859": 0, "869": 0}
        final_balances = {"881": 0, "882": 0, "883": 0, "884": 0, "886": 0}
        for idx in range(len(self._netresult_accounts_map)):
            balance = self._get_account_balance(self._settled_accounts_map[idx], self.move_result_id)
            if balance == 0:
                continue
            settled_account = self.env["account.account"].search([("code", "=", self._settled_accounts_map[idx]),
                                                                  ("company_id", "=", self.company_id.id)])
            netresult_account = self.env["account.account"].search([("code", "=", self._netresult_accounts_map[idx]),
                                                                    ("company_id", "=", self.company_id.id)])
            if not settled_account:
                raise ValidationError(_(f"It's missing account {self._settled_accounts_map[idx]} to compute the settlement result"
                                        f"Please check you chart of acccount and add the account with this code"))

            if not netresult_account:
                raise ValidationError(_(f"It's missing account {self._netresult_accounts_map[idx]} to compute the settlement result"
                                        f"Please check you chart of acccount and add the account with this code"))

            aml_list = self._get_double_move_line_vals(settled_account, netresult_account, balance,
                                                       self.move_netresult_id)
            for aml in aml_list:
                self.env["account.move.line"].with_context(check_move_validity=False).create(aml)
            final_balances[self._netresult_accounts_map[idx]] = balance
        # Compute the tax result based on the sum of 881 + 882 + 883 - 885 - 886
        tax_result = (final_balances["881"] + final_balances["882"] + final_balances["883"] - final_balances["884"] -
                      final_balances["886"]) * (self.tax_id.amount / 100)
        self.tax_result_signed = tax_result
        # Now lets create an account id

    def create_tax_settlement(self):
        # TODO: ADD description to all moves and lines too.
        move_vals = self._get_move_vals()
        move_vals["ref"] = _(f"Settlement {self.fiscal_year} Tax")
        self.move_tax_id = self.env["account.move"].create(move_vals)
        net_results = ["881", "882", "883", "884", "885", "886"]
        net_result = 0
        tax_871_account = self.env["account.account"].search([("code", "=", "871"),
                                                              ("company_id", "=", self.company_id.id)])
        tax_879_account = self.env["account.account"].search([("code", "=", "879"),
                                                              ("company_id", "=", self.company_id.id)])
        tax_885_account = self.env["account.account"].search([("code", "=", "885"),
                                                              ("company_id", "=", self.company_id.id)])

        if tax_871_account and self.tax_result_signed:
            aml_list = self._get_double_move_line_vals(tax_871_account,
                                                       self.tax_id.invoice_repartition_line_ids.mapped("account_id"),
                                                       self.tax_result_signed,
                                                       self.move_tax_id)
            for aml in aml_list:
                self.env["account.move.line"].with_context(check_move_validity=False).create(aml)
        else:
            raise ValidationError(
                _(f"It's missing account 871 to compute the settlement result"
                  f"Please check you chart of acccount and add the account with this code"))

        if tax_879_account and self.tax_result_signed:
            aml_list = self._get_double_move_line_vals(tax_879_account, tax_871_account, self.tax_result_signed,
                                                       self.move_tax_id)
            for aml in aml_list:
                self.env["account.move.line"].with_context(check_move_validity=False).create(aml)
        else:
            raise ValidationError(
                _(f"It's missing account 879 to compute the settlement result"
                  f"Please check you chart of acccount and add the account with this code"))

        if tax_885_account and abs(self.tax_result_signed):
            aml_list = self._get_double_move_line_vals(tax_885_account, tax_879_account, self.tax_result_signed,
                                                       self.move_tax_id)
            for aml in aml_list:
                self.env["account.move.line"].with_context(check_move_validity=False).create(aml)
        else:
            raise ValidationError(
                _(f"It's missing account 885 to compute the settlement result"
                  f"Please check you chart of acccount and add the account with this code"))

        transfer_result_account = self.env["account.account"].search([("code", "=", "889"),
                                                                      ("company_id", "=", self.company_id.id)])
        if not transfer_result_account:
            raise ValidationError(
                _(f"It's missing account 889 to compute the settlement result"
                  f"Please check you chart of acccount and add the account with this code"))

        # net_result = self._get_account_balance("88", self.move_netresult_id, ["889"])
        for idx in range(len(net_results)):
            balance = self._get_account_balance(net_results[idx], self.move_netresult_id)
            if balance == 0:
                balance = self._get_account_balance(net_results[idx], self.move_tax_id)
                if balance == 0:
                    continue

            net_result_account = self.env["account.account"].search([("code", "=", net_results[idx]),
                                                                     ("company_id", "=", self.company_id.id)])
            if net_result_account:
                aml_list = self._get_double_move_line_vals(net_result_account, transfer_result_account, balance,
                                                           self.move_tax_id)
                for aml in aml_list:
                    self.env["account.move.line"].with_context(check_move_validity=False).create(aml)
                net_result += balance
            else:
                raise ValidationError(
                    _(f"It's missing account {net_results[idx]} to compute the settlement result"
                      f"Please check you chart of acccount and add the account with this code"))

        self.net_result = abs(net_result)
        self.net_result_signed = net_result
        self.tax_result = abs(self.tax_result_signed)

    def action_check_draft_moves(self):

        for settlment in self:
            draft_moves = self.env["account.move"].search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("state", "=", "draft"),
                    ("date", ">=", settlment.date_start),
                    ("date", "<=", settlment.date_end),
                ]
            )
            if draft_moves:
                msg = _("There is one or more journal entry found in Draft state: \n")
                for move in draft_moves:
                    msg += "ID: {}, Date: {}, Number: {}, Ref: {}\n".format(
                        move.id,
                        move.date,
                        move.name,
                        move.ref,
                    )
                raise ValidationError(msg)
        return True

    def unlink(self):
        for sr in self:
            if sr.state == "posted":
                raise UserError(_("You cannot delete an result settlement which has been posted."))
