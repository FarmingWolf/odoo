# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta, datetime
from math import ceil, floor
from typing import Dict, List

from odoo.exceptions import UserError
from odoo.tools import start_of, end_of
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyFeeMaintenance(models.Model):
    _name = "estate.lease.contract.property.fee.maintenance"
    _description = "资产租赁合同物业费"
    _order = "date_received"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    contract_rental_plan_rel_id = fields.Many2one(comodel_name='estate.lease.contract.rental.plan.rel',
                                                  string='合同-资产关系表ID', ondelete="set null")
    manage_fee_detail_id = fields.Many2one('estate.lease.contract.property.manage.fee.detail', string="物业费明细ID",
                                           ondelete="set null")
    period_d_start = fields.Date(string="本期开始日", default=lambda self: self._cal_period_d_start(), tracking=True)
    period_d_end = fields.Date(string="本期结束日", default=lambda self: self._cal_period_d_end(), tracking=True)
    maintenance_receivable = fields.Float(default=0.0, string="本期应收(元)", tracking=True, help="账单金额")
    maintenance_received = fields.Float(default=0.0, string="本期实收(元)", tracking=True)

    maintenance_receivable_this = fields.Float(default=0.0, string="本次应收(元)", compute="_compute_received",
                                               store=True, compute_sudo=True)

    date_received = fields.Date(string="实收日期", default=lambda self: fields.Date.context_today(self), tracking=True)
    maintenance_received_2_date = fields.Date(string="实收至", readonly=True, store=True, compute="_compute_received",
                                              compute_sudo=True)
    days_received = fields.Float(string="实收天数", readonly=True, store=True, compute="_compute_received",
                                 compute_sudo=True)
    days_received_sum = fields.Float(string="累计实收天数", readonly=True, store=True, compute="_compute_received",
                                     compute_sudo=True)
    days_arrears = fields.Float(string="欠缴天数", readonly=True, store=True, compute="_compute_received",
                                compute_sudo=True)

    maintenance_received_sum = fields.Float(default=0.0, string="累计实收(元)", readonly=True, compute="_compute_received",
                                            store=True, compute_sudo=True, help="合同保存后，系统自动计算累计值")
    maintenance_arrears = fields.Float(string="本期欠缴(元)", readonly=True, store=True, compute="_compute_received",
                                       compute_sudo=True)
    maintenance_arrears_sum = fields.Float(string="累计欠缴(元)", readonly=True, store=True, compute="_compute_received",
                                           compute_sudo=True, help="合同保存后，系统自动计算累计值")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True,
                                 ondelete="cascade")

    property_id = fields.Many2one('estate.property', related="contract_rental_plan_rel_id.property_id", string="资产",
                                  ondelete="cascade")
    contract_id = fields.Many2one('estate.lease.contract', related="contract_rental_plan_rel_id.contract_id",
                                  string="合同", ondelete="cascade")
    contract_state = fields.Selection(related="contract_id.state", string="合同状态")
    party_a_unit_id = fields.Many2one("estate.lease.contract.party.a.unit", related="contract_id.party_a_unit_id",
                                      ondelete="set null")
    party_a_unit_invisible = fields.Boolean(string="甲方显示与否", related="contract_id.party_a_unit_invisible")
    date_start = fields.Date(string="合同开始日期", related="contract_id.date_start")
    date_rent_start = fields.Date(string="计租开始日期", related="contract_id.date_rent_start")
    date_rent_end = fields.Date(string="计租结束日期", related="contract_id.date_rent_end")
    renter_id = fields.Many2one('res.partner', string="承租人", related='contract_id.renter_id', store=True,
                                ondelete="set null")
    maintenance_receipt = fields.Boolean(string="发票")
    maintenance_receipt_evidence = fields.Html(string="发票信息")
    active = fields.Boolean("数据状态", default=True)

    @api.onchange("maintenance_receivable", "maintenance_received")
    def _onchange_maintenance_receivable(self):
        self.maintenance_arrears = self.maintenance_receivable - self.maintenance_received

    @api.onchange("period_d_start", "period_d_end")
    def _onchange_period_d_start(self):
        # 若独立核算物业费，那么实收记录的period_d_start和period_d_end必须来自物业费明细
        manage_fee_details = self._get_manage_fee_details(self.contract_id, self.property_id)
        if not manage_fee_details:
            if self.period_d_start > self.period_d_end:
                self.period_d_end = end_of(self.period_d_start, 'month')
        else:
            for detail in manage_fee_details:
                if detail.period_date_from <= self.period_d_start <= detail.period_date_to:
                    self.period_d_start = detail.period_date_from
                    self.period_d_end = detail.period_date_to
                    self.maintenance_receivable = detail.manage_fee_receivable
                    return

            if self.period_d_start > self.period_d_end:
                self.period_d_end = end_of(self.period_d_start, 'month')

    def _cal_period_d_start(self):
        # context_d = fields.Date.context_today(self)
        # start_d = start_of(context_d, 'month')
        # return start_d
        _logger.info(f"contract_rental_plan_rel_id={self.contract_rental_plan_rel_id.id}")
        _logger.info(f"manage_fee_detail_id={self.manage_fee_detail_id.id}")

        if self.manage_fee_detail_id:
            _logger.info(f"manage_fee_detail_id.period_date_from={self.manage_fee_detail_id.period_date_from}")
            return self.manage_fee_detail_id.period_date_from

        context_d = fields.Date.context_today(self)
        manage_fee_details = self._get_manage_fee_details(self.contract_id, self.property_id)
        if not manage_fee_details:
            return context_d

        for detail in manage_fee_details:
            if detail.period_date_from <= context_d <= detail.period_date_to:
                return detail.period_date_from

        return context_d


    def _cal_period_d_end(self):
        # context_d = fields.Date.context_today(self)
        # end_d = end_of(context_d, 'month')
        # return end_d
        if self.manage_fee_detail_id:
            return self.manage_fee_detail_id.period_date_to

        context_d = fields.Date.context_today(self)
        manage_fee_details = self._get_manage_fee_details(self.contract_id, self.property_id)
        if not manage_fee_details:
            return context_d

        for detail in manage_fee_details:
            if detail.period_date_from <= context_d <= detail.period_date_to:
                return detail.period_date_to

        return context_d

    @api.depends("maintenance_received", "maintenance_receivable", "date_received")
    def _compute_received(self):
        for record in self:
            # 从物业费方案生成的物业费明细
            if record.manage_fee_detail_id:
                domain = [('manage_fee_detail_id', '=', record.manage_fee_detail_id.id)]
            else:  # 在已发布合同中手动输入的物业费明细
                domain = [('contract_rental_plan_rel_id', '=', record.contract_rental_plan_rel_id.id)]

            rcds = self.env["estate.lease.contract.property.fee.maintenance"].search(domain)

            # 在已发布合同中手动输入物业费明细的计算逻辑（同于水电费的缴费逻辑）：
            if not record.manage_fee_detail_id:
                received_sum = 0.0
                arrears_sum = 0.0

                for rcd in rcds:
                    received_sum += rcd.maintenance_received
                    if rcd.maintenance_received_sum != received_sum:
                        rcd.maintenance_received_sum = received_sum

                    arrears = rcd.maintenance_receivable - rcd.maintenance_received
                    arrears_sum += arrears
                    if rcd.maintenance_arrears != arrears:
                        rcd.maintenance_arrears = arrears

                    if rcd.maintenance_arrears_sum != arrears_sum:
                        rcd.maintenance_arrears_sum = arrears_sum

            else:  # 从物业费方案生成的物业费明细，在物业费明细tab页操作逻辑（同与租金明细的多次缴费逻辑）：
                received_sum = 0.0
                days_cal_sum = 0.0
                received_sum_this_time = 0.0
                days_cal_this_time = 0.0
                days_cal_sum_this_time = 0.0

                for rcd in rcds:
                    received_sum += rcd.maintenance_received
                    if rcd.maintenance_received_sum != received_sum:
                        rcd.maintenance_received_sum = received_sum

                    if record.manage_fee_detail_id.manage_fee_receivable:
                        days_cal = rcd.maintenance_received / record.manage_fee_detail_id.manage_fee_receivable * \
                                   record.manage_fee_detail_id.days_receivable
                        days_cal_sum += days_cal
                        if rcd.days_received != days_cal:
                            rcd.days_received = days_cal

                        if rcd.days_received_sum != days_cal_sum:
                            rcd.days_received_sum = days_cal_sum

                        if rcd.maintenance_arrears != record.manage_fee_detail_id.manage_fee_receivable - rcd.maintenance_received_sum:
                            rcd.maintenance_arrears = record.manage_fee_detail_id.manage_fee_receivable - rcd.maintenance_received_sum

                        # 根据本次实收和欠缴反算本次应收（不同于总应收）
                        if rcd.maintenance_receivable_this != rcd.maintenance_received + rcd.maintenance_arrears:
                            rcd.maintenance_receivable_this = rcd.maintenance_received + rcd.maintenance_arrears

                        if rcd.days_arrears != record.manage_fee_detail_id.days_receivable - rcd.days_received_sum:
                            rcd.days_arrears = record.manage_fee_detail_id.days_receivable - rcd.days_received_sum

                        date_2 = record.manage_fee_detail_id.period_date_from + timedelta(days=rcd.days_received_sum)
                        if rcd.maintenance_received_2_date != date_2:
                            rcd.maintenance_received_2_date = date_2

                        if rcd.date_received <= record.date_received:
                            received_sum_this_time = received_sum
                            days_cal_this_time = days_cal
                            days_cal_sum_this_time = days_cal_sum

                if record.maintenance_received_sum != received_sum_this_time:
                    record.maintenance_received_sum = received_sum_this_time

                if record.days_received != days_cal_this_time:
                    record.days_received = days_cal_this_time

                if record.days_received_sum != days_cal_sum_this_time:
                    record.days_received_sum = days_cal_sum_this_time

                if record.maintenance_arrears != record.manage_fee_detail_id.manage_fee_receivable - record.maintenance_received_sum:
                    record.maintenance_arrears = record.manage_fee_detail_id.manage_fee_receivable - record.maintenance_received_sum

                if record.days_arrears != record.manage_fee_detail_id.days_receivable - record.days_received_sum:
                    record.days_arrears = record.manage_fee_detail_id.days_receivable - record.days_received_sum

                # 计算本次应收（不同于总应收）
                if record.maintenance_receivable_this != record.maintenance_received + record.maintenance_arrears:
                    record.maintenance_receivable_this = record.maintenance_received + record.maintenance_arrears

                date_2_this_time = record.manage_fee_detail_id.period_date_from + timedelta(days=record.days_received_sum)
                if record.maintenance_received_2_date != date_2_this_time:
                    record.maintenance_received_2_date = date_2_this_time

    def _get_manage_fee_details(self, contract_id, property_id):
        if not contract_id or not property_id:
            return []

        tgt_model = 'estate.lease.contract.property.manage.fee.detail'
        tgt_domain = [('contract_id', '=', contract_id.id), ('property_id', '=', property_id.id)]
        details = self.env[tgt_model].search(tgt_domain)
        _logger.info(f"manage_fee_details={details}")
        return details

    @api.model
    def create(self, vals_list):
        context_d = fields.Date.context_today(self)
        if (self.period_d_start == self.period_d_end and self.period_d_start == context_d) or \
                (not self.period_d_start) or (not self.period_d_end):
            self.period_d_start = self._cal_period_d_start()
            self.period_d_end = self._cal_period_d_end()
        _logger.info(f"period_d_start={self.period_d_start};self.period_d_end={self.period_d_end}")

        res = super().create(vals_list)

        return res

    @api.model
    def write(self, vals):

        _logger.info(f"period_d_start={self.period_d_start};self.period_d_end={self.period_d_end}")

        res = super().write(vals)

        return res
