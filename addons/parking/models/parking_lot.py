# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class ParkingLot(models.Model):

    _name = "parking.lot"
    _description = "园区停车场"

    name = fields.Char('园区停车场', required=True, translate=True)
    park_id = fields.Many2one("park", string="园区")
    parking_space_ids = fields.One2many("parking.space", "parking_lot_id", string="停车位")
    parking_space_cnt = fields.Integer(string='停车位数量', compute='_compute_parking_space_count', store=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends('parking_space_ids')
    def _compute_parking_space_count(self):
        for lot in self:
            lot.parking_space_cnt = self.env['parking.space'].search_count([('parking_lot_id', '=', lot.id)])
