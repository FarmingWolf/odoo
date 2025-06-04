# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from addons.utils.models.utils import Utils
from odoo import fields, models, api, _
from odoo.api import ondelete
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, end_of


class ParkingSpaceVehicleRel(models.Model):

    _name = "parking.space.vehicle.rel"
    _description = "车位车辆关系"
    _order = "parking_space_id ASC, park_vehicle_id ASC, start_date ASC"

    name = fields.Char(string="车牌车主电话", related="park_vehicle_id.name")
    parking_space_id = fields.Many2one("parking.space", string="停车位", ondelete="restrict", required=True)
    park_vehicle_id = fields.Many2one("park.vehicle", string="车辆", ondelete="restrict", required=True)
    vehicle_owner_id = fields.Many2one("res.partner", string="车主", related="park_vehicle_id.driver_id")
    vehicle_owner_mobile_phone = fields.Char(string="电话", compute="_compute_mobile_phone")
    start_date = fields.Date(string="开始日期", required=True)
    end_date = fields.Date(string="结束日期", required=True)
    assignation_log_id = fields.Many2one('park.vehicle.assignation.log', string="租约历史", ondelete="restrict")
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends('park_vehicle_id.name', 'park_vehicle_id.driver_id.name', 'vehicle_owner_mobile_phone')
    def _compute_name(self):
        for record in self:
            record.name = ((record.park_vehicle_id.name or "") + "-" +
                           (record.park_vehicle_id.driver_id.name or "") + "-" + (record.vehicle_owner_mobile_phone or ""))

    @api.depends('park_vehicle_id.driver_phone', 'park_vehicle_id.driver_mobile')
    def _compute_mobile_phone(self):
        for record in self:
            record.vehicle_owner_mobile_phone = record.park_vehicle_id.driver_mobile or record.park_vehicle_id.driver_phone

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):

        if default is None:
            default = {}

        default.update({
            'start_date': self.end_date + timedelta(days=1),
            'end_date': end_of(self.end_date + timedelta(days=(self.end_date - self.start_date).days), 'month'),
        })
        return super().copy(default)

    def _check_period_duplicate(self):
        """
        1、同一车位，同一期间段内，只能接受同一车主两辆车
        2、同一车主可能换车，但是不同的车的期间不能重叠
        3、同一车辆不能在同一期间段内绑定不同车位
        """
        for record in self:
            rcd_existed = self.search(
                [('parking_space_id', '=', record.parking_space_id.id), ('active', '=', True),
                 ('end_date', '>=', record.start_date), ('start_date', '<=', record.end_date)], order="start_date")
            err_msg = []
            inf_msg = []
            for r in rcd_existed:
                if record.park_vehicle_id.driver_id == r.park_vehicle_id.driver_id:
                    inf_msg.append({'车主': r.park_vehicle_id.driver_id.name or '', '车牌号': r.park_vehicle_id.license_plate,
                                    '开始日期': r.start_date, '结束日期': r.end_date})
                else:
                    err_msg.append({'车主': r.park_vehicle_id.driver_id.name or '', '车牌号': r.park_vehicle_id.license_plate,
                                    '开始日期': r.start_date, '结束日期': r.end_date})

            if err_msg:
                msg_disp = " ".join(
                    [f"{msg['车主']}/{msg['车牌号']}:{msg['开始日期']}至{msg['结束日期']}" for msg in err_msg])
                raise ValidationError(f"同一车位同一时间段内不能为不同车主注册车辆。"
                                      f"本车位{record.parking_space_id.name},车辆{record.park_vehicle_id.name}"
                                      f"在{record.start_date}至{record.end_date}"
                                      f"与不同车主的车辆有期间重叠：{msg_disp}")

            # 同一车主不能在同一期间超过两辆
            if inf_msg:
                duplicate_lst = Utils.check_overlap_rules(inf_msg, start_date_key="开始日期", end_date_key="结束日期")
                err_msg = []
                for tgt_lst in duplicate_lst:
                    err_msg.append(f"如下{len(tgt_lst['overlapping_objects'])}个期间段有重叠：")
                    i = 0
                    for tgt in tgt_lst["overlapping_objects"]:
                        i += 1
                        err_msg.append(f"第{i}个：{tgt['车主']}/{tgt['车牌号']}/{str(tgt['开始日期'])}至{str(tgt['结束日期'])}；")

                if err_msg:
                    raise ValidationError(f"同一车主同一车位上同一期间内不能注册超过两辆车。而本车位{err_msg}")

            rcd_existed = self.search(
                [('park_vehicle_id', '=', record.park_vehicle_id.id), ('active', '=', True),
                 ('end_date', '>=', record.start_date), ('start_date', '<=', record.end_date)], order="start_date")
            for r in rcd_existed:
                if r.id == record.id:
                    continue
                err_msg.append({'车位': r.parking_space_id.name, '车辆': r.park_vehicle_id.license_plate,
                                '开始日期': r.start_date, '结束日期': r.end_date})

            if err_msg:
                msg_disp = " ".join(
                    [f"{msg['车位']}/{msg['车辆']}:{msg['开始日期']}至{msg['结束日期']}" for msg in err_msg])
                raise ValidationError(f"同一车辆在同一期间段内不能重复注册！请检查车辆:{record.park_vehicle_id.license_plate},"
                                      f"车位{record.parking_space_id.name}在{record.start_date}至{record.end_date}期间"
                                      f"与以下时间段有重叠：{msg_disp}")

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._check_period_duplicate()

        assignation_record = {
            'vehicle_id': record.park_vehicle_id.id,
            'date_start': record.start_date,
            'date_end': record.end_date,
            'parking_space_id': record.parking_space_id.id,
        }
        assignation_log = self.env['park.vehicle.assignation.log'].create(assignation_record)
        record.assignation_log_id = assignation_log.id

        return record

    def write(self, vals):

        res = super().write(vals)
        self._check_period_duplicate()

        assignation_record = {
            'vehicle_id': self.park_vehicle_id.id,
            'date_start': self.start_date,
            'date_end': self.end_date,
            'parking_space_id': self.parking_space_id.id,
        }
        self.env['park.vehicle.assignation.log'].browse(self.assignation_log_id.id).write(assignation_record)

        return res
