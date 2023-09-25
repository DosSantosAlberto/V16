# -*- conding: utf-8 -*-
from odoo.tests import common
from odoo.tests import Form
import unittest
from odoo.exceptions import ValidationError


class TestSaleOrder(common.TransactionCase):

    def test_check_discount(self):

        test_sale_order = self.env['sale.order'].create({'partner_id': 2,
                                                    'partner_invoice_id': 1,
                                                    'partner_shipping_id': 2,
                                                    'pricelist_id': 3})
        test_produt_order = self.env['sale.order.line'].create({

            'produt_id':2,
            'produt_uom_qty':20,
            'price_unit':147,
            'discount':105,
            'tax_id':False,
            'customer_lead':0.0,
            'name': "[E-COM06] Corner Desk Right Sit",

        })
        if test_produt_order['discount'] < 0 and test_produt_order['discount'] > 100:
           return  ValidationError("the discount must be between 0 and 100 %.")

        self.assertEqual(test_produt_order,ValidationError("the discount must be between 0 and 100 %."))


