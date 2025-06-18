# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class MeetingMinutesType(models.Model):

    _name = "meeting.minutes.type"
    _inherit = 'meeting.minutes.type'
    _description = "Meeting minutes type"
    _order = "sequence ASC"

    name_show = fields.Char(string="Meeting Minutes Type Show", compute="_compute_name_show",)
    mandatory = fields.Boolean(string="Mandatory", default=True)

    @api.depends('name', 'mandatory')
    def _compute_name_show(self):
        for record in self:
            if record.mandatory:
                record.name_show = record.name + "（必传）"
            else:
                record.name_show = record.name + "（非必传）"
