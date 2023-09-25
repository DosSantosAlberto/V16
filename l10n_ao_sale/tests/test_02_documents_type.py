from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('aliengroup')
class TestDocumentsType(TransactionCase):

    def setUp(self):
        super(TestDocumentsType, self).setUp()

        # Search the res.company
        self.company = self.env['res.company'].search([('id', '=', 1)], limit=1)
        # Search the ir.sequence
        self.ir_sequence_ids = self.env['ir.sequence'].search(
            [('company_id', '=', self.company.id), ('code', 'in', ['OU', 'OR', 'PP'])])

    def _check_documents_type_search(self, ir_sequences_code):
        result = self.env['sale.order.document.type'].search([('code', 'in', ir_sequences_code)],
                                                  order='id desc').mapped(
            'code')
        expected_result = ['PP', 'OR', 'OU']
        self.assertEqual(result, expected_result)

    def test_validation_documents_type(self):
        self._check_documents_type_search(self.ir_sequence_ids.mapped("code"))
