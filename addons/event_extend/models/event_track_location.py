# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, is_html_empty

_logger = logging.getLogger(__name__)


class EventTrackLocation(models.Model):

    _description = "活动地点"
    _inherit = ['event.track.location']

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
