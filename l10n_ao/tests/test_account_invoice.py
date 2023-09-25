from odoo.tests import TransactionCase


class TestSAFTAccountInvoice(TransactionCase):

    def setUp(self):
        super(TestSAFTAccountInvoice, self).setUp()
        #self.create_customer_invoice_1()
        #self.create_customer_invoice_2()

    def create_customer_invoice_1(self):
        self.env.user.company_id.tax_calculation_rounding_method = 'round_globally'

        payment_term = self.env.ref('account.account_payment_term_advance')
        journalrec = self.env['account.journal'].search([('type', '=', 'sale')])[0]
        partner3 = self.env.ref('base.res_partner_3')
        account_id = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id

        # Configurar os impostos com campos saft
        tax1 = self.env['account.tax'].create({
            'name': 'Tax 15.0',
            'amount': 15.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'saft_wth_type': '',
            'exemption_reason': ''
        })

        tax3 = self.env['account.tax'].create({
            'name': 'Tax 10.0',
            'amount': 10.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'saft_wth_type': '',
            'exemption_reason': ''
        })

        tax2 = self.env['account.tax'].create({
            'name': 'Tax 5.0',
            'amount': 5.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'saft_wth_type': '',
            'exemption_reason': ''
        })

        invoice_line_data = [
            (0, 0,
             {
                 'product_id': self.env.ref('product.product_product_1').id,
                 'quantity': 40.0,
                 'account_id': account_id,
                 'name': 'product test 1',
                 'discount': 10.00,
                 'price_unit': 2.27,
                 'invoice_line_tax_ids': [(6, 0, [tax1.id])],
             }
             ),
            (0, 0,
             {
                 'product_id': self.env.ref('product.product_product_2').id,
                 'quantity': 21.0,
                 'account_id': self.env['account.account'].search(
                     [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
                 'name': 'product test 2',
                 'discount': 0.0,
                 'price_unit': 2.77,
                 'invoice_line_tax_ids': [(6, 0, [tax2.id])],
             }
             ),
            (0, 0,
             {
                 'product_id': self.env.ref('product.product_product_3').id,
                 'quantity': 21.0,
                 'account_id': self.env['account.account'].search(
                     [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
                 'name': 'product test 3',
                 'discount': 10.00,
                 'price_unit': 2.77,
                 'invoice_line_tax_ids': [(6, 0, [tax3.id])],
             }
             )
        ]

        invoice = self.env['account.invoice'].create(dict(
            name="Test Customer Invoice",
            payment_term_id=payment_term.id,
            journal_id=journalrec.id,
            partner_id=partner3.id,
            invoice_line_ids=invoice_line_data
        ))

    def create_customer_invoice_2(self):
        self.env.user.company_id.tax_calculation_rounding_method = 'round_globally'

        payment_term = self.env.ref('account.account_payment_term_advance')
        journalrec = self.env['account.journal'].search([('type', '=', 'sale')])[0]
        partner2 = self.env.ref('base.res_partner_2')
        account_id = self.env['account.account'].search(
            [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id

        # Configurar os impostos com campos saft
        tax1 = self.env['account.tax'].create({
            'name': 'Tax 25.0',
            'amount': 25.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        tax3 = self.env['account.tax'].create({
            'name': 'Tax 20.0',
            'amount': 20.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        tax2 = self.env['account.tax'].create({
            'name': 'Tax 6.0',
            'amount': 6.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        invoice_line_data = [
            (0, 0,
             {
                 'product_id': self.env.ref('product.product_product_1').id,
                 'quantity': 40.0,
                 'account_id': account_id,
                 'name': 'product test 1',
                 'discount': 10.00,
                 'price_unit': 2.27,
                 'invoice_line_tax_ids': [(6, 0, [tax1.id])],
             }
             ),
            (0, 0,
             {
                 'product_id': self.env.ref('product.product_product_2').id,
                 'quantity': 21.0,
                 'account_id': self.env['account.account'].search(
                     [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
                 'name': 'product test 2',
                 'discount': 0.0,
                 'price_unit': 2.77,
                 'invoice_line_tax_ids': [(6, 0, [tax2.id])],
             }
             ),
            (0, 0,
             {
                 'product_id': self.env.ref('product.product_product_3').id,
                 'quantity': 21.0,
                 'account_id': self.env['account.account'].search(
                     [('user_type_id', '=', self.env.ref('account.data_account_type_revenue').id)], limit=1).id,
                 'name': 'product test 3',
                 'discount': 10.00,
                 'price_unit': 2.77,
                 'invoice_line_tax_ids': [(6, 0, [tax3.id])],
             }
             )
        ]

        invoice = self.env['account.invoice'].create(dict(
            name="Test Customer Invoice",
            payment_term_id=payment_term.id,
            journal_id=journalrec.id,
            partner_id=partner2.id,
            invoice_line_ids=invoice_line_data
        ))


    def test_get_saft_data(self):

        invoices = self.env["account.invoice"].search([])
        #signed_doc = utils.sign_document("2018-05-18;2018-05-18T11:22:19;FAC 001/18;53.00;")
        #print(signed_doc)

        result = invoices.get_saft_data()
        print("\n\n\n")
        print(result)

