from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_is_zero, ustr
from datetime import datetime
from ast import literal_eval
from collections import defaultdict

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter


class AOAccountReport(models.Model):
    _inherit = "account.report"

    def _compute_formula_batch_with_engine_domain(self, options, date_scope, formulas_dict, current_groupby,
                                                  next_groupby, offset=0, limit=None):
        """ Report engine.

        Formulas made for this engine consist of a domain on account.move.line. Only those move lines will be used to compute the result.

        This engine supports a few subformulas, each returning a slighlty different result:
        - sum: the result will be sum of the matched move lines' balances

        - sum_if_pos: the result will be the same as sum only if it's positive; else, it will be 0

        - sum_if_neg: the result will be the same as sum only if it's negative; else, it will be 0

        - count_rows: the result will be the number of sublines this expression has. If the parent report line has no groupby,
                      then it will be the number of matching amls. If there is a groupby, it will be the number of distinct grouping
                      keys at the first level of this groupby (so, if groupby is 'partner_id, account_id', the number of partners).
        """

        def _format_result_depending_on_groupby(formula_rslt):
            if not current_groupby:
                if formula_rslt:
                    # There should be only one element in the list; we only return its totals (a dict) ; so that a list is only returned in case
                    # of a groupby being unfolded.
                    return formula_rslt[0][1]
                else:
                    # No result at all
                    return {
                        'sum': 0,
                        'sum_if_pos': 0,
                        'sum_if_neg': 0,
                        'sum_if_plus1year': 0,  # Added for Angola reports
                        'sum_if_less1year': 0,  # Added for Angola Reports
                        'sum_if_5year': 0,  # Added for Angola reports
                        'sum_if_plus5year': 0,  # Added for Angola Reports
                        'count_rows': 0,
                        'has_sublines': False,
                    }
            return formula_rslt

        self._check_groupby_fields(
            (next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        groupby_sql = f'account_move_line.{current_groupby}' if current_groupby else None
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        rslt = {}

        for formula, expressions in formulas_dict.items():
            line_domain = literal_eval(formula)
            tables, where_clause, where_params = self._query_get(options, date_scope, domain=line_domain)

            tail_query, tail_params = self._get_engine_query_tail(offset, limit)

            # for expression in expressions:
            #     if 'sum_if_less1year' in expression.subformula:
            #         where_clause += ''' AND ("account_move_line".date_maturity::date <= ("account_move_line".date::date + '1 year'::interval)) '''
            #     if 'sum_if_plus1year' in expression.subformula:
            #         where_clause += ''' AND ("account_move_line".date_maturity::date > ("account_move_line".date::date + '1 year'::interval)) '''
            #     if 'sum_if_5year' in expression.subformula:
            #         where_clause += ''' AND "account_move_line".date_maturity <= "account_move_line".date + '5 year'::interval
            #                     AND "account_move_line".date_maturity > "account_move_line".date + '1 year'::interval '''
            #     if 'sum_if_plus5year' in expression.subformula:
            #         where_clause += ''' AND "account_move_line".date_maturity > "account_move_line".date + '5 year'::interval '''

            query = f"""
                SELECT
                    COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS sum,
                    COALESCE(SUM(CASE WHEN account_move_line.date_maturity::date <= (account_move_line.date::date + '1 year'::interval) 
                    THEN ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END), 0.0) AS sum_if_less1year,
                    COALESCE(SUM(CASE WHEN account_move_line.date_maturity::date > (account_move_line.date::date + '1 year'::interval) 
                    THEN ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END), 0.0) AS sum_if_plus1year,
                    COALESCE(SUM(CASE WHEN account_move_line.date_maturity <= account_move_line.date + '5 year'::interval 
                    AND account_move_line.date_maturity > account_move_line.date + '1 year'::interval 
                    THEN ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END), 0.0) AS sum_if_5year,
                    COALESCE(SUM(CASE WHEN account_move_line.date_maturity > account_move_line.date + '5 year'::interval 
                    THEN ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) END), 0.0) AS sum_if_plus5year,
                    COUNT(DISTINCT account_move_line.{next_groupby.split(',')[0] if next_groupby else 'id'}) AS count_rows
                    {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}
                FROM {tables}
                JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                {f' GROUP BY {groupby_sql}' if groupby_sql else ''}
                {tail_query}
            """

            # Fetch the results.
            formula_rslt = []
            self._cr.execute(query, where_params + tail_params)
            all_query_res = self._cr.dictfetchall()

            total_sum = 0
            for query_res in all_query_res:
                res_sum = query_res['sum']
                total_sum += res_sum
                totals = {
                    'sum': res_sum,
                    'sum_if_pos': 0,
                    'sum_if_neg': 0,
                    'sum_if_plus1year': query_res['sum_if_plus1year'],
                    'sum_if_less1year': query_res['sum_if_less1year'],
                    'sum_if_5year': query_res['sum_if_5year'],  # Added for Angola reports
                    'sum_if_plus5year': query_res['sum_if_plus5year'],  # Added for Angola Reports
                    'count_rows': query_res['count_rows'],
                    'has_sublines': query_res['count_rows'] > 0,
                }
                formula_rslt.append((query_res.get('grouping_key', None), totals))

            # Handle sum_if_pos, -sum_if_pos, sum_if_neg and -sum_if_neg
            expressions_by_sign_policy = defaultdict(lambda: self.env['account.report.expression'])
            subformula_without_sign = 0
            for expression in expressions:
                subformula_without_sign = expression.subformula.replace('-', '').strip()
                if subformula_without_sign in ('sum_if_pos', 'sum_if_neg'):
                    expressions_by_sign_policy[subformula_without_sign] += expression
                elif subformula_without_sign in (
                        'sum_if_less1year', 'sum_if_plus1year', 'sum_if_5year', 'sum_if_plus5year'):
                    expressions_by_sign_policy[subformula_without_sign] += expression
                else:
                    expressions_by_sign_policy['no_sign_check'] += expression

            if expressions_by_sign_policy['sum_if_less1year'] or expressions_by_sign_policy['sum_if_plus1year'] or \
                    expressions_by_sign_policy['sum_if_5year'] or expressions_by_sign_policy['sum_if_plus5year']:
                for subformula, expression in expressions_by_sign_policy.items():
                    if subformula in ('sum_if_less1year', 'sum_if_plus1year', 'sum_if_5year', 'sum_if_plus5year'):
                        formula_rslt_with_sign = [(grouping_key, {**totals, subformula: totals[subformula], }) for
                                                  grouping_key, totals in formula_rslt]

                        if expressions_by_sign_policy[subformula]:
                            rslt[(formula, expressions_by_sign_policy[subformula])] = _format_result_depending_on_groupby(
                                formula_rslt_with_sign)
                        else:
                            rslt[(formula, expressions_by_sign_policy[subformula])] = _format_result_depending_on_groupby(
                                [])
                    elif expressions_by_sign_policy['no_sign_check']:
                        rslt[(
                        formula, expressions_by_sign_policy['no_sign_check'])] = _format_result_depending_on_groupby(
                            formula_rslt)

            # Then we have to check the total of the line and only give results if its sign matches the desired policy.
            # This is important for groupby managements, for which we can't just check the sign query_res by query_res
            if expressions_by_sign_policy['sum_if_pos'] or expressions_by_sign_policy['sum_if_neg']:
                sign_policy_with_value = 'sum_if_pos' if self.env.company.currency_id.compare_amounts(total_sum,
                                                                                                      0.0) >= 0 else 'sum_if_neg'
                # >= instead of > is intended; usability decision: 0 is considered positive

                formula_rslt_with_sign = [(grouping_key, {**totals, sign_policy_with_value: totals['sum']}) for
                                          grouping_key, totals in formula_rslt]

                for sign_policy in ('sum_if_pos', 'sum_if_neg'):
                    policy_expressions = expressions_by_sign_policy[sign_policy]

                    if policy_expressions:
                        if sign_policy == sign_policy_with_value:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby(
                                formula_rslt_with_sign)
                        else:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby([])

            if expressions_by_sign_policy['no_sign_check']:
                rslt[(formula, expressions_by_sign_policy['no_sign_check'])] = _format_result_depending_on_groupby(
                    formula_rslt)

        return rslt

    def _get_columns_name(self, options):
        """
        Override
        Return the name of the columns of the follow-ups report
        """
        headers = super(AOAccountReport, self)._get_columns_name(options)
        if self.ao_report:
            headers.insert(1, {'name': _('Notes')})
        return headers


class AOAccountFinancialReportLine(models.Model):
    # _name = "account.financial.html.report.line"
    _inherit = "account.report.line"

    note = fields.Char("Note")
