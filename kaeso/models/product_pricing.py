import math
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

PERIOD_RATIO = {'hour': 1, 'day': 24, 'week': 24 * 7}


class KaesoProductPricing(models.Model):
    _inherit = 'product.pricing'

    def _compute_price(self, duration, unit):
        """Compute the price for a specified duration of the current pricing rule.
        :param float duration: duration in hours
        :param str unit: duration unit (hour, day, week)
        :return float: price
        """
        self.ensure_one()
        price = self.env.context.get('price', self.price)

        if duration <= 0 or self.recurrence_id.duration <= 0:
            return price
        if unit != self.recurrence_id.unit:
            converted_duration = math.ceil(
                (duration * PERIOD_RATIO[unit]) / (self.recurrence_id.duration * PERIOD_RATIO[self.recurrence_id.unit]))
        else:
            converted_duration = math.ceil(duration / self.recurrence_id.duration)
        return price * converted_duration

