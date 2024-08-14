# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class ParkingSpace(models.Model):

    _name = "parking.space"
    _description = "园区停车位"

    name = fields.Char('园区停车位', required=True, translate=True)
    park_id = fields.Many2one("park", string="园区", compute="_compute_park_id", store=True)
    parking_space_type_id = fields.Many2one("parking.space.type", string="停车位类型", store=True)
    parking_lot_id = fields.Many2one("parking.lot", string="园区停车场")
    color = fields.Integer()
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends('parking_lot_id')
    def _compute_park_id(self):
        for record in self:
            if record.parking_lot_id:
                record.park_id = record.parking_lot_id.park_id.id
