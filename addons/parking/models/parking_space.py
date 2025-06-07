# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from addons.utils.models.utils import Utils
from odoo import fields, models, api
from odoo.api import ondelete, _logger
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import float_compare


class ParkingSpace(models.Model):

    _name = "parking.space"
    _description = "园区停车位"
    _order = "park_id ASC, parking_lot_id ASC, parking_space_type_id ASC, sequence ASC, name ASC"

    name = fields.Char('园区停车位', required=True, translate=True)
    sequence = fields.Integer("排序", default=1, compute='_compute_sequence', store=True)
    park_id = fields.Many2one("park", string="园区", store=True, related="parking_lot_id.park_id", ondelete="restrict")
    parking_space_type_id = fields.Many2one("parking.space.type", string="停车位类型", store=True, ondelete="restrict")
    parking_lot_id = fields.Many2one("parking.lot", string="园区停车场", ondelete="restrict")
    color = fields.Integer(related="parking_space_type_id.color")
    vehicle_bound = fields.One2many('parking.space.vehicle.rel', inverse_name="parking_space_id", string="当前绑定车辆",
                                    domain=[('end_date', '>=', fields.Date.today())])
    reserved = fields.Boolean("固定车位", default=False)
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

    def copy(self, default=None):

        if default is None:
            default = {}

        default.update({
            'name': self.name + "(复制)",
            'sequence': self.sequence + 1
        })
        return super().copy(default)

    def action_bind_parking_space_vehicle(self):

        default_parking_space_id = self.env.context.get('default_parking_space_id')
        _logger.info(f"default_parking_space_id={default_parking_space_id}")
        tgt_rel_ids = False
        tgt_domain = []
        if default_parking_space_id:
            tgt_domain = [('parking_space_id', '=', default_parking_space_id)]
            date_today = datetime.today()
            # tgt_domain.append(('start_date', '<=', date_today))
            tgt_domain.append(('end_date', '>=', date_today))
            tgt_domain.append(('active', '=', True))
            tgt_rel_ids = self.env['parking.space.vehicle.rel'].search(tgt_domain).ids

        action = {
            'name': "车位绑定车辆",
            'type': 'ir.actions.act_window',
            'res_model': 'parking.space.vehicle.rel',
            'view_mode': 'tree,form',
            'res_id': tgt_rel_ids,
            'context': {'default_parking_space_id': default_parking_space_id, 'from_parking_space_page': True},
            'target': 'new',
            'domain': tgt_domain,
        }
        return action

    @staticmethod
    def get_parking_space_cnt(company_id, env, reserved=False):

        search_domain = [('company_id', '=', company_id)]
        if reserved:
            search_domain.append(('reserved', '=', True))

        spots_cnt = env['parking.space'].sudo().search_count(search_domain)

        return spots_cnt

    @staticmethod
    def get_parking_space_reserved_bound(company_id, env):

        reserved_spots = env['parking.space'].sudo().search([('company_id', '=', company_id), ('reserved', '=', True)])
        spots_bound = 0
        vehicle_bound = 0
        for spot in reserved_spots:
            if len(spot.vehicle_bound) > 0:
                spots_bound += 1
                vehicle_bound += len(spot.vehicle_bound)

        return spots_bound, vehicle_bound

    @staticmethod
    def get_parking_spaces_with_type(company_id, env):
        search_domain = [('company_id', '=', company_id)]
        spaces_cnt_by_type = env['parking.space'].sudo()._read_group(search_domain,
                                                                     ['parking_space_type_id'], ['vehicle_id'])
        return spaces_cnt_by_type