from odoo.addons.account.tests.account_test_classes import AccountingTestCase
import time


class TestPaymentWithhold(AccountingTestCase):

    def setUp(self):
        super(TestPayment, self).setUp()
        self.register_payments_model = self.env['account.register.payments']
        self.payment_model = self.env['account.payment']
        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.acc_bank_stmt_model = self.env['account.bank.statement']
        self.acc_bank_stmt_line_model = self.env['account.bank.statement.line']

        self.partner_agrolait = self.env.ref("base.res_partner_2")
        self.currency_aoa_id = self.env.ref("base.AOA").id

    def create_invoice(self, amount=10000, type='out_invoice', currency_id=None):
        """ Returns an open invoice """
        invoice = self.invoice_model.create({
            'partner_id': self.partner_agrolait.id,
            'reference_type': 'none',
            'currency_id': currency_id,
            'name': type == 'out_invoice' and 'invoice to client' or 'invoice to supplier',
            'account_id': self.account_receivable.id,
            'type': type,
            'date_invoice': time.strftime('%Y') + '-11-26',
        })
        self.invoice_line_model.create({
            'quantity': 1,
            'price_unit': amount,
            'invoice_id': invoice.id,
            'name': 'Service',
            'account_id': self.account_revenue.id,
            'invoce_line_tax_ids': (4, 0, [self.env.ref("account_tax_retencao_sale")])
        })
        invoice.action_invoice_open()
        return invoice

    def test_full_payment_process(self):
        """ Create a payment for two invoices, post it and reconcile it with a bank statement """
        inv_1 = self.create_invoice(amount=10000, currency_id=self.currency_aoa_id)
        # inv_2 = self.create_invoice(amount=1, currency_id=self.currency_aoa_id)

        ctx = {'active_model': 'account.invoice', 'active_ids': [inv_1.id]}
        register_payments = self.register_payments_model.with_context(ctx).create({
            'payment_date': time.strftime('%Y') + '-11-15',
            'journal_id': self.bank_journal_aoa.id,
            'payment_method_id': self.payment_method_manual_in.id,
        })
        register_payments.create_payment()
        payment = self.payment_model.search([], order="id desc", limit=1)

        self.assertAlmostEquals(payment.amount, 10000)
        self.assertEqual(payment.state, 'posted')
        self.assertEqual(inv_1.state, 'paid')
        # self.assertEqual(inv_2.state, 'paid')

        self.check_journal_items(payment.move_line_ids, [
            {'account_id': self.account_aoa.id, 'debit': 10000.0, 'credit': 0.0, 'amount_currency': 0,
             'currency_id': False},
            {'account_id': inv_1.account_id.id, 'debit': 0.0, 'credit': 9350.0, 'amount_currency': 00,
             'currency_id': False},
        ])

        liquidity_aml = payment.move_line_ids.filtered(lambda r: r.account_id == self.account_eur)
        bank_statement = self.reconcile(liquidity_aml, 200, 0, False)

        self.assertEqual(liquidity_aml.statement_id, bank_statement)
        self.assertEqual(liquidity_aml.move_id.statement_line_id, bank_statement.line_ids[0])

        self.assertEqual(payment.state, 'reconciled')
