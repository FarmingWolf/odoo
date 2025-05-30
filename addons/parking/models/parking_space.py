# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from addons.utils.models.utils import Utils
from odoo import fields, models, api
from odoo.api import ondelete
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class ParkingSpace(models.Model):

    _name = "parking.space"
    _description = "园区停车位"
    _order = "park_id, parking_lot_id, parking_space_type_id, sequence, name"

    name = fields.Char('园区停车位', required=True, translate=True)
    sequence = fields.Integer("排序", default=1, compute='_compute_sequence', store=True)
    park_id = fields.Many2one("park", string="园区", store=True, related="parking_lot_id.park_id", ondelete="restrict")
    parking_space_type_id = fields.Many2one("parking.space.type", string="停车位类型", store=True, ondelete="restrict")
    parking_lot_id = fields.Many2one("parking.lot", string="园区停车场", ondelete="restrict")
    color = fields.Integer(related="parking_space_type_id.color")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends("name", "park_id", "parking_space_type_id","parking_lot_id")
    def _compute_sequence(self):
        for space in self:
            all_rcds = self.search([('company_id', '=', self.company_id.id)],
                                   order="park_id asc, parking_lot_id asc, parking_space_type_id asc, sequence asc, name asc")
            set_sequence = False
            max_sequence = len(all_rcds)
            same_type = False
            max_sequence_same_type = 0
            for rcd in all_rcds:
                max_sequence= rcd.sequence
                if space.park_id != rcd.park_id or space.parking_lot_id != rcd.parking_lot_id:
                    continue
                if space.parking_space_type_id.id < rcd.parking_space_type_id.id:
                    continue
                if space.parking_space_type_id == rcd.parking_space_type_id:
                    same_type = True
                    if space.id == rcd.id:  # 跳过自己
                        break
                    max_sequence_same_type = rcd.sequence
                    if Utils.compare_strings(space.with_context(lang='zh_CN').name,
                                             rcd.with_context(lang='zh_CN').name) < 0:
                        if space.sequence != rcd.sequence - 1:
                            space.sequence = rcd.sequence - 1
                        set_sequence = True
                        break
                if not same_type and space.parking_space_type_id.id > rcd.parking_space_type_id.id:
                    if space.sequence != rcd.sequence - 1:
                        space.sequence = rcd.sequence - 1
                    set_sequence = True
                    break

            if not set_sequence:
                if same_type:
                    if space.sequence != max_sequence_same_type + 1:
                        space.sequence = max_sequence_same_type + 1
                else:
                    if space.sequence != max_sequence:
                        space.sequence = max_sequence

    @api.onchange("park_id", "parking_space_type_id","parking_lot_id", "name")
    def _onchange_sequence(self):
        self._compute_sequence()