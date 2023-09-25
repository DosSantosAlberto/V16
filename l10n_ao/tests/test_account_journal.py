from odoo.tests import TransactionCase
from odoo import fields

class TestSAFTAccountAccount(TransactionCase):

    def setUp(self):
        super(TestSAFTAccountAccount, self).setUp()

    def test_get_saft_data(self):
        journal = self.env["account.journal"].search([])
        today = fields.Date.today()
        start_date = fields.Date.start_of(today, "month")
        end_date = fields.Date.end_of(today, "month")
        result = journal.with_context(start_date=start_date, end_date=end_date).get_saft_data()
        print("\n\n\n")
        print(result)

