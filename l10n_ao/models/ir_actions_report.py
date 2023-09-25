from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class IrActionsReportAO(models.Model):
    _inherit = 'ir.actions.report'

    filter_domain = fields.Char("Condition", help="Domain to define which condition the document can be printed")
    no_print_message = fields.Char("Message", help="Message in case can't not be printed")
    print_control = fields.Boolean("Print Control")

    # @override the method to add printing control features to the report.
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Return an action of type ir.actions.report.

        :param res_ids: id/ids/browserecord of the records to print (if not used, pass an empty list)
        :param data: Name of the template to generate an action for
        """
        report_sudo = self._get_report(report_ref)

        if report_sudo.filter_domain and report_sudo.no_print_message and res_ids:
            domain = [('id', 'in', res_ids)] + safe_eval(report_sudo.filter_domain, report_sudo._get_eval_context())
            result = self.env[report_sudo.model].search(domain)
            if not result:
                raise UserError(report_sudo.no_print_message)

        if report_sudo.print_control:
            model_instance = self.env[report_sudo.model].browse(res_ids)
            for instance in model_instance:
                instance.print_counter = instance.print_counter + 1

        return super(IrActionsReportAO, self)._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
