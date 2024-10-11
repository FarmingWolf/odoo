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

    rental_detail_id = fields.Many2one('estate.lease.contract.property.rental.detail', string="租金明细ID")

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

            date_2_this_time = record.rental_detail_id.period_date_from + timedelta(days=record.days_received_sum)
            if record.rental_received_2_date != date_2_this_time:
                record.rental_received_2_date = date_2_this_time
