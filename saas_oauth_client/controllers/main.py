# Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import json
import requests
import werkzeug
import urllib.parse
import logging

import odoo
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.utils import ensure_db
from odoo.addons.web.controllers.home import Home
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class AuthQuickMaster(http.Controller):

    def get_saas_url(self):
        return request.env['ir.config_parameter'].sudo().get_param('saas_oauth.server')

    def get_database_url(self):
        url = request.httprequest.url
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme + "://" + parsed.netloc

    @http.route('/saas/login', type="http", auth='public')
    def login(self, database_login=None, database_user_id=None):
        if not (database_login or database_user_id):
            return "Wrong args"

        if database_user_id:
            user = request.env['res.users'].sudo().browse(int(database_user_id))
            database_login = user.login
        else:
            user = request.env['res.users'].sudo().search([('login', '=', database_login)])
            database_user_id = user.id

        _logger.debug('Authentication request for %s (id %s)', database_login, database_user_id)
        database_url = self.get_database_url()
        database_id = request.env['ir.config_parameter'].sudo().get_param('saas_oauth.database', 'unknown')
        saas_url = self.get_saas_url()
        params = urllib.parse.urlencode({
            'database_id': database_id,
            'database_login': database_login,
            'database_user_id': database_user_id,
            'database_url': database_url,
        })
        url = urllib.parse.urljoin(saas_url, '/saas/get-token?%s' % params)

        return werkzeug.utils.redirect(url, 302)

    @http.route('/saas/check-token', type="http", auth='public', methods=["GET"], csfr=False)
    def check_token(self, token, test_cr=False):
        saas_url = self.get_saas_url()
        url = urllib.parse.urljoin(saas_url, '/saas/check-token')
        res = requests.post(
            url,
            data=json.dumps({"params": {"token": token}}),
            headers={"Content-Type": "application/json"}, verify=False)
        _logger.debug('Response from saas odoo: %s', res.text)
        result = res.json().get('result')
        if not result.get('success'):
            return result.get('error')

        database_login = result['data']['database_login']
        user = request.env['res.users'].sudo().search([('login', '=', database_login)])
        user.write({'saas_oauth_token': token})
        _logger.info('Successful Authentication as %s via token %s', database_login, token)

        if test_cr is False:
            # A new cursor is used to authenticate the user and it cannot see the
            # latest changes of current transaction.
            # Therefore we need to make the commit.

            # TODO: tests
            # In test mode, one special cursor is used for all transactions.
            # So we don't need to make the commit. More over commit() shall not be used,
            # because otherwise test changes are not rollbacked at the end of test
            request.env.cr.commit()

        request.session.authenticate(request.db, database_login, token)
        return werkzeug.utils.redirect('/')


# ----------------------------------------------------------
# Odoo Web web Controllers Override to allow redirect
# users when their service is suspended
# ----------------------------------------------------------
class SaaSHome(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        service_suspended = request.env['ir.config_parameter'].sudo().search([("key", "=", "saas_oauth.service_suspended")])
        if service_suspended:
            saas_url = request.env['ir.config_parameter'].sudo().get_param("saas_oauth.server")
            database_id = request.env['ir.config_parameter'].sudo().get_param("saas_oauth.database")
            if saas_url and database_id:
                redirect = '%s/service/suspension/%s' % (saas_url, database_id)
                return werkzeug.utils.redirect(redirect,307)
        if not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)
        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)

        request.update_env(user=request.session.uid)

        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')
