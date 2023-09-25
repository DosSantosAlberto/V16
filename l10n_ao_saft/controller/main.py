from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition

class SAFTController(http.Controller):

    @http.route('/web/download/saft/<int:file_id>', type='http', auth='user')
    def download_saft(self, file_id, **kwargs):

        saft_file = request.env["l10nao.saft.file"].search([("id", "=", file_id)])
        return request.make_response(saft_file.text,
                                 [('Content-Type', 'application/xml'),
                                  ('Content-Disposition', content_disposition(saft_file.name + ".xml"))])
