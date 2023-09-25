from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SAFTAccountAccount(models.Model):
    _inherit = "account.account"

    def get_saft_data(self):

        start_date = self._context.get("start_date")
        end_date = self._context.get("end_date")
        customers = suppliers = self.env["res.partner"]
        taxes = self.env["account.tax"]
        journals = self.env["account.journal"]

        if not start_date or not end_date:
            raise ValidationError(_("Start date or end period date are not defined!"))

        result = {"GeneralLedgerAccounts":{
            "Account": []
        }}

        for account in self.filtered(lambda r: not r.deprecated):
            close_debit_balance = close_credit_balance = 0.0

            #if not account.group_id:
            #    raise ValidationError(_(
            #        "The account %s doesn't have a group defined. For SAFT file this is a requirement!") % account.code)

            move_lines = self.env["account.move.line"].search(
                [("account_id", "=", account.id), ("date", ">=", fields.Date.to_string(start_date)),
                 ("date", "<=", fields.Date.to_string(end_date)), ("company_id", '=', self.company_id.id)])

            if not move_lines:
                continue

            journals |= move_lines.mapped("journal_id")

            for line in move_lines:
                close_debit_balance += line.debit
                close_credit_balance += line.credit
                if line.journal_id.type == "sale":
                    customers |= line.partner_id
                if line.journal_id.type == "purchase":
                    suppliers |= line.partner_id
                if line.tax_line_id:
                    taxes |= line.tax_line_id
                if line.tax_ids:
                    taxes |= line.tax_ids

            account_val = {

                    "AccountID": account.code,
                    "AccountDescription": account.name,
                    "OpeningDebitBalance": account.opening_debit,
                    "OpeningCreditBalance": account.opening_credit,
                    "ClosingDebitBalance": round(close_debit_balance,6),
                    "ClosingCreditBalance": round(close_credit_balance,6),
                    "GroupingCategory": "GM",
                    "GroupingCode": account.group_id.code_prefix_start,
            }

            result["GeneralLedgerAccounts"]["Account"].append(account_val)
            # result["customers"] = customers
            # result["suppliers"] = suppliers
            # result["journals"] = journals
            # result["taxes"] = taxes


        return result
