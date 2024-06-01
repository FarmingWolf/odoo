# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class ParkingSpaceType(models.Model):

    _name = "parking.space.type"
    _description = "园区停车位类型"

    name = fields.Char('停车位类型', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1, help="按类型排序")

    _sql_constraints = [
        ('name', 'unique(name)', '类型不能重复')
    ]
