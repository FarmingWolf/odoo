# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from math import ceil, floor
from typing import Dict, List

from odoo.exceptions import UserError
from odoo.tools import start_of, end_of
from . import estate_lease_contract
from odoo import fields, models, api
from ...utils.models.utils import Utils

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyFeeWater(models.Model):
    _name = "estate.lease.contract.property.fee.water"
    _description = "资产租赁合同水费"
    _order = "date_received"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    contract_rental_plan_rel_id = fields.Many2one(comodel_name='estate.lease.contract.rental.plan.rel',
                                                  string='合同-资产关系表ID', required=True, ondelete="cascade")
    period_d_start = fields.Date(string="本期开始日", default=lambda self: self._cal_period_d_start(), tracking=True)
    period_d_end = fields.Date(string="本期结束日", default=lambda self: self._cal_period_d_end(), tracking=True)
    water_receivable = fields.Float(default=0.0, string="本期应收(元)", tracking=True, help="账单金额")
    water_received = fields.Float(default=0.0, string="本期实收(元)", tracking=True)

    date_received = fields.Date(string="实收日期", default=lambda self: fields.Date.context_today(self), tracking=True)
    water_received_sum = fields.Float(default=0.0, string="累计实收(元)", readonly=True, compute="_compute_received",
                                      store=True, compute_sudo=True, help="合同保存后，系统自动计算累计值")
    water_arrears = fields.Float(string="本期欠缴(元)", readonly=True, store=True, compute="_compute_received",
                                 compute_sudo=True)
    water_arrears_sum = fields.Float(string="累计欠缴(元)", readonly=True, store=True, compute="_compute_received",
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

    @api.onchange("water_receivable", "water_received")
    def _onchange_water_receivable(self):
        self.water_arrears = self.water_receivable - self.water_received

    @api.onchange("period_d_start")
    def _onchange_period_d_start(self):
        self.period_d_end = end_of(self.period_d_start, "month")

    @api.onchange("period_d_end")
    def _onchange_period_d_end(self):
        self.period_d_start = start_of(self.period_d_end, "month")

    def _cal_period_d_start(self):
        context_d = fields.Date.context_today(self)
        start_d = start_of(context_d, 'month')
        return start_d

    def _cal_period_d_end(self):
        context_d = fields.Date.context_today(self)
        end_d = end_of(context_d, 'month')
        return end_d

    @api.depends("water_received", "water_receivable", "date_received")
    def _compute_received(self):
        for record in self:
            domain = [('contract_rental_plan_rel_id', '=', record.contract_rental_plan_rel_id.id)]
            rcds = self.env["estate.lease.contract.property.fee.water"].search(domain)
            received_sum = 0.0
            arrears_sum = 0.0

            for rcd in rcds:
                received_sum += rcd.water_received
                if rcd.water_received_sum != received_sum:
                    rcd.water_received_sum = received_sum

                arrears = rcd.water_receivable - rcd.water_received
                arrears_sum += arrears
                if rcd.water_arrears != arrears:
                    rcd.water_arrears = arrears

                if rcd.water_arrears_sum != arrears_sum:
                    rcd.water_arrears_sum = arrears_sum
