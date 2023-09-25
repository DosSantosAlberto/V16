from odoo.tests import TransactionCase,tagged
from odoo import fields
import datetime

@tagged('-at_install', 'post_install')
class TestSAFTAccountAccount(TransactionCase):

    def setUp(self):
        super(TestSAFTAccountAccount, self).setUp()



    def test_get_saft_data(self):
        accounts = self.env["account.account"].search([])
        today = fields.Date.today()
        #today = datetime.date(2019, 4, 15)
        start_date = fields.Date.start_of(today, "month")
        end_date = fields.Date.end_of(today, "month")
        result = accounts.with_context(start_date=start_date, end_date=end_date).get_saft_data()
        print("\n\n\n")
        print(result)
