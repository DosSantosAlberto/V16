from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_country(self):
        return self.env.ref('base.ao')

    @api.model
    def _default_state(self):
        """return Luanda state"""
        return self.env.ref("l10n_ao_base.state_ao_11")

    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=_default_country)
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', default=_default_state)
    city = fields.Char(default='Luanda')
    sector = fields.Selection([('public', 'Public Sector'), ('private', 'Private Sector')], default='private')

