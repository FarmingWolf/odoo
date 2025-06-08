# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ParkVehicleAssignationLog(models.Model):
    _name = "park.vehicle.assignation.log"
    _description = "Drivers history on a vehicle"
    _order = "date_start desc"

    name = fields.Char(related="vehicle_id.name", store=True, readonly=True)
    vehicle_id = fields.Many2one('park.vehicle', string="Vehicle", required=True)
    driver_id = fields.Many2one('res.partner', string="Vehicle Owner", related="vehicle_id.driver_id", readonly=True)
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    lease_contract_nm = fields.Char(string="Estate Lease Contract", readonly=True)
    lease_contract_id = fields.Integer(string="Estate Lease Contract ID", readonly=True)
    parking_space_id = fields.Many2one('parking.space', string="Parking Space")
    active = fields.Boolean("Active", default=True)

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    def _check_period_duplicate(self):
        for record in self:
            rcd_existed = self.search(
                [('vehicle_id', '=', record.vehicle_id.id), ('active', '=', True),
                 ('date_end', '>=', record.date_start), ('date_start', '<=', record.date_end)], order="date_start")

            err_msg = []
            for r in rcd_existed:
                if r.id == record.id:
                    continue
                err_msg.append({'车辆': r.vehicle_id.name, '开始日期': r.date_start, '结束日期': r.date_end})

            if err_msg:
                msg_disp = " ".join([f"{msg['车辆']}:{msg['开始日期']}至{msg['结束日期']}" for msg in err_msg])
                raise ValidationError(f"同一车辆在同一期间段内不能重复注册！"
                                      f"车辆【{record.vehicle_id.name}】在{record.date_start}至{record.date_end}期间"
                                      f"与以下期间有重叠：{msg_disp}")

    def write(self, vals):
        res = super().write(vals)
        self._check_period_duplicate()
        return res

    @api.model
    def create(self, vals_list):
        record = super().create(vals_list)
        record._check_period_duplicate()
        return record

    @staticmethod
    def get_vehicles_cnt(company_id, env):
        s_domain = [('date_start', '<=', date.today()),
                    ('date_end', '>=', date.today())]

        vehicles_cnt_by_company = env['park.vehicle.assignation.log'].sudo()._read_group(s_domain,
                                                                                         ['company_id'],
                                                                                         ['vehicle_id:count_distinct'])

        return vehicles_cnt_by_company

    @staticmethod
    def get_vehicles_cnt_by_term(company_id, env, long_term=1):
        s_domain = [('date_start', '<=', date.today()), ('date_end', '>=', date.today()),
                    ('company_id', '=', company_id)]

        long_term_vehicles = env['park.vehicle.assignation.log'].sudo().search(s_domain)
        vehicles_cnt = len(long_term_vehicles)
        long_term_cnt = 0
        for v in long_term_vehicles:
            if (v.date_end - v.date_start).days >= long_term:
                long_term_cnt += 1

        return {
            "vehicles_cnt": vehicles_cnt,
            "long_term_cnt": long_term_cnt,
            "short_term_cnt": vehicles_cnt - long_term_cnt
        }
