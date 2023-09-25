# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.date_utils import get_month, get_fiscal_year
from odoo.tools.misc import format_date


import re
from collections import defaultdict
import json


class ReSequenceWizardAo(models.TransientModel):
    _inherit ="account.resequence.wizard"


    def resequence(self):
        super(ReSequenceWizardAo, self).resequence()
        for move_id in self.move_ids:
            if move_id.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                move_id.resign(move_id)
