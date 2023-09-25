import logging
import os
from odoo import http
from odoo.http import request
from zipfile import ZipFile
import base64, os, tempfile

_logger = logging.getLogger(__name__)


class KaesoMainControllers(http.Controller):

    @http.route(['/remuneration/map/download'], type='http', auth="user", website=True)
    def query_download(self, dir_path_file, **kw):
        _logger.info("Download file %s" % dir_path_file)
        with open(dir_path_file, 'rb') as f:
            file_data = f.read()

        return request.make_response(file_data, [('Content-Type', 'application/octet-stream'),
                                                 ('Content-Disposition', f'attachment; filename="{dir_path_file}"')])
