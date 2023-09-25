from odoo.tests import TransactionCase

class TestSAFTProduct(TransactionCase):

    def setUp(self):
        super(TestSAFTProduct,self).setUp()
        #self.create_product()
        #self.test_get_saft_data()

    def create_product(self):

        product = self.env['product.product'].create({

            'name': "arroz",
            'description': "este arroz é muito bom",
            'default_code': "12345",
            'categ_id': 1,
            'saft_type': '',
            'unnumber': '1244',
            'customs_details': 'hoje'

        })
        print(product)

    def test_get_saft_data(self):

        product = self.env["product.product"].search([])
        result = product.get_saft_data()
        print("\n\n\n")
        print(result)

