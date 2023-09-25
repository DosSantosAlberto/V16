# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import TransactionCase, tagged
import datetime


@tagged('aliengroup')
class TestSaleOrder(TransactionCase):

    def setUp(self):
        super(TestSaleOrder, self).setUp()
        # Search the res.company
        self.company = self.env['res.company'].sudo().search([('id', '=', 1)], limit=1)
        # Search the res.partner
        self.partner = self.company.partner_id

    def test_01_or_validation_validity_date(self):
        # Search Document Type -> Proposal
        self.doc_type = self.env['sale.order.document.type'].sudo().search([('code', '=', 'OR')], limit=1)
        # Create the SO with four order lines
        self.sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner.id,
            'document_type_id': self.doc_type.id,
            'validity_date': datetime.date.today(),
        })
        expected_result = datetime.date.today()
        self.assertEqual(self.sale_order.validity_date, expected_result)

    def test_02_pp_validation_validity_date(self):
        # Search Document Type -> Pro Forma
        self.doc_type = self.env['sale.order.document.type'].sudo().search([('code', '=', 'PP')], limit=1)
        # Create the SO with four order lines
        self.sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner.id,
            'document_type_id': self.doc_type.id,
            'validity_date': datetime.date.today(),
        })
        expected_result = datetime.date.today()
        self.assertEqual(self.sale_order.validity_date, expected_result)

    def test_03_or_validation_exclusive_product_product(self):
        # Search Document Type -> Quotation
        self.doc_type = self.env['sale.order.document.type'].sudo().search([('code', '=', 'OR')], limit=1)
        # Create Product type product service
        self.product_service = self.env['product.template'].sudo().create({
            'name': 'Demo -> Service Product',
            'type': 'service',
            'list_price': 500,
        })
        self.product_consu = self.env['product.template'].sudo().create({
            'name': 'Demo -> Consumable Product',
            'type': 'consu',
            'list_price': 1000,
        })
        # Create the SO
        self.sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner.id,
            'document_type_id': self.doc_type.id,
            'validity_date': datetime.date.today(),
        })
        # Create the SO with four order lines
        self.service_prod_order = self.env['sale.order.line'].sudo().create({
            'name': self.product_service.product_variant_id.name,
            'product_id': self.product_service.product_variant_id.id,
            'product_uom_qty': 1,
            'price_unit': self.product_service.product_variant_id.list_price,
            'order_id': self.sale_order.id,
        })
        self.consu_prod_order = self.env['sale.order.line'].sudo().create({
            'name': self.product_consu.product_variant_id.name,
            'product_id': self.product_consu.product_variant_id.id,
            'product_uom_qty': 1,
            'price_unit': self.product_consu.product_variant_id.list_price,
            'order_id': self.sale_order.id,
        })
        result = self.sale_order.action_validate()
        expected_result = {}
        self.assertEqual(result, expected_result)

    def test_04_pp_validation_exclusive_service_product(self):
        # Search Document Type -> Pro Forma
        self.doc_type = self.env['sale.order.document.type'].sudo().search([('code', '=', 'PP')], limit=1)
        # Create Product type product product
        self.product_product = self.env['product.template'].sudo().create({
            'name': 'Demo -> Service Product',
            'type': 'service',
            'list_price': 1500,
        })
        self.product_consu = self.env['product.template'].sudo().create({
            'name': 'Demo -> Consumable Product',
            'type': 'consu',
            'list_price': 1000,
        })
        # Create the SO
        self.sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner.id,
            'document_type_id': self.doc_type.id,
            'validity_date': datetime.date.today(),
        })
        # Create the SO with four order lines
        self.service_prod_order = self.env['sale.order.line'].sudo().create({
            'name': self.product_product.name,
            'product_id': self.product_product.id,
            'product_uom_qty': 1,
            'price_unit': self.product_product.list_price,
            'order_id': self.sale_order.id,
        })
        self.consu_prod_order = self.env['sale.order.line'].sudo().create({
            'name': self.product_consu.product_variant_id.name,
            'product_id': self.product_consu.product_variant_id.id,
            'product_uom_qty': 1,
            'price_unit': self.product_consu.product_variant_id.list_price,
            'order_id': self.sale_order.id,
        })
        result = self.sale_order.action_validate()
        expected_result = {}
        self.assertEqual(result, expected_result)
