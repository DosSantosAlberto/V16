from odoo.tests import TransactionCase


class TestSAFTAccountPayment(TransactionCase):

    def setUp(self):
        super(TestSAFTAccountPayment, self).setUp()

    def test_get_saft_data(self):

        payment = self.env['account.payment'].search([])
        result = payment.get_saft_data()
        print(result)
        print("####################################")

