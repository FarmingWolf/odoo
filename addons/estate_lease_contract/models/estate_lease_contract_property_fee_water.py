# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta, date
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

    name = fields.Char(string="水费实缴详情", default="水费实缴详情")
    contract_rental_plan_rel_id = fields.Many2one(comodel_name='estate.lease.contract.rental.plan.rel', readonly=True,
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
    receipt_status = fields.Selection(string="发票状态", selection=[('applied', '已申请，未开票'), ('done', '已开票')],
                                      default=None, tracking=True, compute="_compute_receipt_status", store=True)
    receipt_type = fields.Selection(string="发票类型", selection=[('zp', '专票'), ('pp', '普票')],
                                    default=None, tracking=True, store=True)
    receipt_type_editable = fields.Boolean(string="发票类型可编辑",
                                           compute="_compute_receipt_type_editable")
    receipt_apply_uid = fields.Many2one(string="发票申请人", comodel_name="res.users", tracking=True)
    receipt_apply_date = fields.Date(string="发票申请时间", tracking=True)
    water_receipt = fields.Boolean(string="发票")
    water_receipt_evidence = fields.Html(string="发票信息")
    water_receipt_editable = fields.Boolean(string="发票信息可编辑",
                                            compute="_compute_water_receipt_editable")
    receipt_done_by_uid = fields.Many2one(string="发票开具人", comodel_name="res.users", tracking=True)
    receipt_done_date = fields.Date(string="发票开具时间", tracking=True)

    def _compute_water_receipt_editable(self):
        for record in self:
            record.water_receipt_editable = \
                self.env.user.has_group('estate_lease_contract.contract_brokerage_invoice_manage')

    def _compute_receipt_type_editable(self):
        is_editable = self.env.user.has_group('estate.estate_group_business')
        for record in self:
            if not is_editable:
                record.receipt_type_editable = False
            else:
                if record.water_receipt:
                    record.receipt_type_editable = False
                else:
                    record.receipt_type_editable = True

    @api.onchange("water_receivable", "water_received")
    def _onchange_water_receivable(self):
        self.water_arrears = self.water_receivable - self.water_received

    @api.onchange("period_d_start", "period_d_end")
    def _onchange_period_d_start(self):
        if self.period_d_start > self.period_d_end:
            self.period_d_end = end_of(self.period_d_start, 'month')

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

    def action_apply_water_invoice(self):
        for record in self:
            if record.water_received < 0.01:
                raise UserError("开票金额有误！")
            if record.receipt_status != 'applied':
                record.receipt_status = 'applied'
                record.receipt_apply_uid = self.env.user.id
                record.receipt_apply_date = date.today()
                record._set_default_water_receipt_evidence()

            if not record.receipt_type:
                record.receipt_type = 'zp'

    @api.onchange("water_receipt")
    def _onchange_water_receipt(self):
        if self.water_receipt:
            self.receipt_done_by_uid = self.env.user.id
            self.receipt_done_date = date.today()
            self._set_default_water_receipt_evidence()

    @api.depends("water_receipt", "water_receipt_evidence")
    def _compute_receipt_status(self):
        for record in self:
            if record.water_receipt and record.water_receipt_evidence:
                if record.receipt_status != 'done':
                    record.receipt_status = 'done'
                    record.receipt_done_by_uid = self.env.user.id
                    record.receipt_done_date = date.today()
            else:
                if record.receipt_status == 'done':
                    record.receipt_status = 'applied'

    def _set_default_water_receipt_evidence(self):
        if not self.water_receipt_evidence:
            tmp_str = []
            if self.renter_id:
                if self.renter_id.is_company:
                    tmp_str.append(f"企业统一信用代码:{str(self.renter_id.vat)}")
                    tmp_str.append(f"开票名称：{str(self.renter_id.name)}")
                else:
                    tmp_str.append(f"开票对象：个人")
                    tmp_str.append(f"开票名称：{str(self.renter_id.name)}")

            if self.receipt_apply_uid:
                tmp_str.append(f"申请人：{self.receipt_apply_uid.name}")
                tmp_str.append(f"申请时间：{self.receipt_apply_date}")

            self.water_receipt_evidence = tmp_str
