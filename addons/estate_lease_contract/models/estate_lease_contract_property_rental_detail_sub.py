# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from math import ceil, floor
from typing import Dict, List

from odoo.exceptions import UserError
from . import estate_lease_contract
from odoo import fields, models, api
from ...utils.models.utils import Utils

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyRentalDetailSub(models.Model):
    _name = "estate.lease.contract.property.rental.detail.sub"
    _description = "资产租赁合同租金明细子批次"
    _order = "date_received"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    rental_detail_id = fields.Many2one('estate.lease.contract.property.rental.detail', string="租金明细ID",
                                       ondelete="cascade")

    rental_receivable_this = fields.Float(default=0.0, string="本次应收(元)", compute="_compute_received",
                                          store=True, compute_sudo=True)
    rental_received = fields.Float(default=0.0, string="本次实收(元)", tracking=True)

    date_received = fields.Date(string="实收日期", default=lambda self: fields.Date.context_today(self), tracking=True)
    rental_received_sum = fields.Float(default=0.0, string="累计实收(元)", readonly=True, compute="_compute_received",
                                       store=True, compute_sudo=True)
    days_received = fields.Float(string="实收天数", readonly=True, store=True, compute="_compute_received",
                                 compute_sudo=True)
    days_received_sum = fields.Float(string="累计实收天数", readonly=True, store=True, compute="_compute_received",
                                     compute_sudo=True)
    rental_arrears = fields.Float(string="欠缴金额", readonly=True, store=True, compute="_compute_received",
                                  compute_sudo=True)
    days_arrears = fields.Float(string="欠缴天数", readonly=True, store=True, compute="_compute_received",
                                compute_sudo=True)
    rental_received_2_date = fields.Date(string="实收至", readonly=True, store=True, compute="_compute_received",
                                         compute_sudo=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True,
                                 ondelete="cascade")

    # 以下字段要在页面显示
    property_id = fields.Many2one('estate.property', related="rental_detail_id.property_id", string="资产",
                                  ondelete="cascade")
    contract_id = fields.Many2one('estate.lease.contract', related="rental_detail_id.contract_id", string="合同",
                                  ondelete="cascade")
    contract_state = fields.Selection(related="contract_id.state", string="合同状态")
    party_a_unit_id = fields.Many2one("estate.lease.contract.party.a.unit", related="contract_id.party_a_unit_id",
                                      ondelete="set null")
    party_a_unit_invisible = fields.Boolean(string="甲方显示与否", related="contract_id.party_a_unit_invisible")
    date_start = fields.Date(string="合同开始日期", related="contract_id.date_start")
    date_rent_start = fields.Date(string="计租开始日期", related="contract_id.date_rent_start")
    date_rent_end = fields.Date(string="计租结束日期", related="contract_id.date_rent_end")
    renter_id = fields.Many2one('res.partner', string="承租人", related='contract_id.renter_id', store=True,
                                ondelete="set null")
    contract_amount = fields.Float(string="合同总额（元）", related='contract_id.contract_amount')
    rental_receivable_tgt_period = fields.Float(string="指定期间应收（元）", related='rental_detail_id.rental_receivable')
    rental_received_tgt_period = fields.Float(string="指定期间实收（元）", related='rental_detail_id.rental_received')
    rental_arrears_tgt_period = fields.Float(string="指定期间欠缴（元）", related='rental_detail_id.rental_arrears')
    period_date_from = fields.Date(string="本期开始日", related="rental_detail_id.period_date_from")
    period_date_to = fields.Date(string="本期结束日", related="rental_detail_id.period_date_to")
    date_payment = fields.Date(string="本期约定支付日", related="rental_detail_id.date_payment")
    rental_period_no = fields.Integer(string="本期期数", related="rental_detail_id.rental_period_no")
    active = fields.Boolean(related="rental_detail_id.active", store=True)

    @api.depends("rental_received", "date_received")
    def _compute_received(self):
        for record in self:
            domain = [('rental_detail_id', '=', record.rental_detail_id.id)]
            rcds = self.env["estate.lease.contract.property.rental.detail.sub"].search(domain)
            received_sum = 0.0
            days_cal_sum = 0.0
            received_sum_this_time = 0.0
            days_cal_this_time = 0.0
            days_cal_sum_this_time = 0.0

            for rcd in rcds:
                received_sum += rcd.rental_received
                if rcd.rental_received_sum != received_sum:
                    rcd.rental_received_sum = received_sum

                if record.rental_detail_id.rental_receivable:
                    days_cal = rcd.rental_received / record.rental_detail_id.rental_receivable * \
                               record.rental_detail_id.days_receivable
                    days_cal_sum += days_cal
                    if rcd.days_received != days_cal:
                        rcd.days_received = days_cal

                    if rcd.days_received_sum != days_cal_sum:
                        rcd.days_received_sum = days_cal_sum

                    if rcd.rental_arrears != record.rental_detail_id.rental_receivable - rcd.rental_received_sum:
                        rcd.rental_arrears = record.rental_detail_id.rental_receivable - rcd.rental_received_sum

                    # 根据本次实收和欠缴反算本次应收（不同于总应收）
                    if rcd.rental_receivable_this != rcd.rental_received + rcd.rental_arrears:
                        rcd.rental_receivable_this = rcd.rental_received + rcd.rental_arrears

                    if rcd.days_arrears != record.rental_detail_id.days_receivable - rcd.days_received_sum:
                        rcd.days_arrears = record.rental_detail_id.days_receivable - rcd.days_received_sum

                    date_2 = record.rental_detail_id.period_date_from + timedelta(days=rcd.days_received_sum)
                    if rcd.rental_received_2_date != date_2:
                        rcd.rental_received_2_date = date_2

                    if rcd.date_received <= record.date_received:
                        received_sum_this_time = received_sum
                        days_cal_this_time = days_cal
                        days_cal_sum_this_time = days_cal_sum

            if record.rental_received_sum != received_sum_this_time:
                record.rental_received_sum = received_sum_this_time

            if record.days_received != days_cal_this_time:
                record.days_received = days_cal_this_time

            if record.days_received_sum != days_cal_sum_this_time:
                record.days_received_sum = days_cal_sum_this_time

            if record.rental_arrears != record.rental_detail_id.rental_receivable - record.rental_received_sum:
                record.rental_arrears = record.rental_detail_id.rental_receivable - record.rental_received_sum

            if record.days_arrears != record.rental_detail_id.days_receivable - record.days_received_sum:
                record.days_arrears = record.rental_detail_id.days_receivable - record.days_received_sum

            # 计算本次应收（不同于总应收）
            if record.rental_receivable_this != record.rental_received + record.rental_arrears:
                record.rental_receivable_this = record.rental_received + record.rental_arrears

            date_2_this_time = record.rental_detail_id.period_date_from + timedelta(days=record.days_received_sum)
            if record.rental_received_2_date != date_2_this_time:
                record.rental_received_2_date = date_2_this_time
