from odoo import fields, models, api, _
from odoo.exceptions import Warning

period_dict = {
    '0': _("Opening"),
    '12': _("Ordinary entries"),
    '13': _("Regularization entries"),
    '14': _("Clearance"),
    '15': _("Closing")
}


class AccountFiscalYear(models.Model):
    _inherit = 'account.fiscal.year'
    _description = 'Account Fiscal Year'

    state = fields.Selection([('open', 'Open'), ('closed', 'Closed')], string="State", default="open")
    periods = fields.Many2many(comodel_name="account.fiscal.period", string="Period")

    @api.model
    def create(self, vals):
        result = super(AccountFiscalYear, self).create(vals)
        period = self.ordinary_entries(result)
        result.periods |= period
        return result

    def unlink(self):
        for res in self:
            moves = self.env['account.move'].search([('year', '=', res.id)])
            if moves:
                raise Warning(_("Impossible to eliminate year with movements"))
        super(AccountFiscalYear, self).unlink()

    def write(self, vals):
        for res in self:
            if vals.get("periods"):
                if vals.get("periods")[0][2]:
                    for period_model in res.periods:
                        if period_model.id not in vals.get("periods")[0][2]:
                            moves = self.env['account.move'].search([('period', '=', period_model.id)])
                            if moves:
                                raise Warning(_("Impossible to eliminate Period with movements"))
                else:
                    for period_model in res.periods:
                        moves = self.env['account.move'].search([('period', '=', period_model.id)])
                        if moves:
                            raise Warning(_("Impossible to eliminate Period with movements"))
        super(AccountFiscalYear, self).write(vals)

    def ordinary_entries(self, year_model):
        """
        normal entries of account move
        :param year_model:
        :return:
        """
        period = self.env['account.fiscal.period'].create({
            'year': year_model.id,
            'start_date': year_model.date_from,
            'end_date': year_model.date_to,
            'period': '12',  # this is normal entries
            'company_id': year_model.company_id.id,
        })
        return period

    def button_close(self):
        self.state = 'closed'


class AccountFiscalPeriod(models.Model):
    _name = 'account.fiscal.period'
    _description = 'Fiscal Period'

    name = fields.Char(string="Name", compute='_compute_name')
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    period = fields.Selection([
        ('0', _("Opening")),
        ('12', _("Ordinary entries")),
        ('13', _("Regularization entries")),
        ('14', _("Clearance")),
        ('15', _("Closing"))
    ], string="Period")
    year = fields.Many2one(comodel_name='account.fiscal.year', string="Fiscal Year")
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id,
                                 string="Company")

    def unlink(self):
        for res in self:
            moves = self.env['account.move'].search([('period', '=', res.id)])
            if moves:
                raise Warning(_("Impossible to eliminate Period with movements"))
        super(AccountFiscalPeriod, self).unlink()

    @api.depends('period')
    def _compute_name(self):
        for res in self:
            res.name = period_dict[res.period]

    @api.constrains('start_date')
    def validate_date(self):
        if self.start_date > self.end_date:
            raise Warning(_("The start date cannot be greater than the end date"))


class Setup(models.TransientModel):
    _inherit = 'account.financial.year.op'

    year = fields.Many2one(related='company_id.accounting_year', required=1, readonly=False)

    @api.onchange('year')
    def onchange_year(self):
        if self.year:
            self.opening_date = self.year.date_from
            self.fiscalyear_last_day = self.year.date_to.day
            self.fiscalyear_last_month = str(self.year.date_to.month)
