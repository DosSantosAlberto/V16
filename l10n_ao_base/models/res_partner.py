from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    county_id = fields.Many2one("res.country.state.county", string="County")

    @api.onchange('state_id')
    def _onchange_state_id_id(self):
        if self.state_id:
            return {'domain': {'county_id': [('state_id', '=', self.state_id.id)]}}
        else:
            return {'domain': {'county_id': []}}