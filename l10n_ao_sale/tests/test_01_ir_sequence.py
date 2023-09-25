# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('aliengroup')
class TestIrSequence(TransactionCase):

    def setUp(self):
        super(TestIrSequence, self).setUp()

        # Search the res.country
        self.country = self.env['res.country'].sudo().search(
            [('code', '=', 'AO')], limit=1)
        # Create the Sequence
        self.company = self.env['res.company'].sudo().create({
            'name': 'Alien Group Test',
            'country_id': self.country.id,
            'city': 'Luanda',
            'regime_iva': 'geral',
            'website': 'www.alien-group.com'
        })

    def _check_company_search(self, company):
        result = self.env['res.company'].search([('id', '=', company.id)])
        expected_result = 'Alien Group Test'
        self.assertEqual(result.name, expected_result)

    def _check_ir_sequence_search(self, company):
        result = self.env['ir.sequence'].search(
            [('company_id', '=', company.id)]).mapped('code')
        expected_result = ['PP', 'OR', 'OU']
        result = [x for x in result if x == 'OU' or x == 'OR' or x == 'PP']
        self.assertEqual(result, expected_result)

    def test_validation_company(self):
        # Tests before creating an ir_sequence
        self._check_company_search(self.company)

    def test_validation_ir_sequence(self):
        self._check_ir_sequence_search(self.company)
