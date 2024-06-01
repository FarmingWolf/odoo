# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class Park(models.Model):

    _name = "park"
    _description = "园区"

    name = fields.Char('园区', required=True, translate=True)
    parking_lot_ids = fields.One2many("parking.lot", "park_id", string="停车场")
    parking_lot_cnt = fields.Integer(string='停车场数量', compute='_compute_parking_lot_count', store=True)
    parking_space_cnt = fields.Integer(string='停车位数量', compute='_compute_parking_space_count', store=True)

    @api.depends('parking_lot_ids')
    def _compute_parking_lot_count(self):
        for park in self:
            park.parking_lot_cnt = self.env['parking.lot'].search_count([('park_id', '=', park.id)])

    @api.depends('parking_lot_ids')
    def _compute_parking_space_count(self):
        for park in self:
            records = self.env['parking.lot'].search([('park_id', '=', park.id)])
            park.parking_space_cnt = sum(record.parking_space_cnt for record in records)
