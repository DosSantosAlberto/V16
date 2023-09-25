# Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
import logging
from odoo import models, fields
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    saas_oauth_token = fields.Char()

    def _check_credentials(self, password, user_agent_env):
        try:
            return super(ResUsers, self)._check_credentials(password, user_agent_env)
        except AccessDenied:
            res = self.sudo().search([('id', '=', self.env.uid), ('saas_oauth_token', '=', password)])
            if not res:
                raise
