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


class EstateLeaseContractPropertyTax(models.Model):
    _name = "estate.lease.contract.property.tax"
    _description = "Property Tax"
    _order = "date_received"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="房产税实缴详情", default="房产税实缴详情")
    contract_rental_plan_rel_id = fields.Many2one(comodel_name='estate.lease.contract.rental.plan.rel', readonly=True,
                                                  string='合同-资产关系表ID', required=True, ondelete="cascade")
    tax_receivable_this = fields.Float(default=0.0, string="本次应收(元)", compute="_compute_received",
                                       store=True, compute_sudo=True)
    tax_received = fields.Float(default=0.0, string="本次实收(元)", tracking=True)

    date_received = fields.Date(string="实收日期", default=lambda self: fields.Date.context_today(self), tracking=True)
    tax_received_sum = fields.Float(default=0.0, string="累计实收(元)", readonly=True, compute="_compute_received",
                                    store=True, compute_sudo=True)
    tax_arrears = fields.Float(string="欠缴金额", readonly=True, store=True, compute="_compute_received",
                               compute_sudo=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True,
                                 ondelete="cascade")

    # 以下字段要在页面显示
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
    contract_amount = fields.Float(string="合同总额（元）", related='contract_id.contract_amount')
    tax_receivable = fields.Float(string="房产税应收（元）", related='contract_rental_plan_rel_id.property_tax_receivable')
    receipt_status = fields.Selection(string="发票状态", selection=[('applied', '已申请，未开票'), ('done', '已开票')],
                                      default=None, tracking=True, compute="_compute_receipt_status", store=True)
    receipt_type = fields.Selection(string="发票类型", selection=[('zp', '专票'), ('pp', '普票')],
                                    default=None, tracking=True, store=True)
    receipt_type_editable = fields.Boolean(string="发票类型可编辑",
                                           compute="_compute_receipt_type_editable")
    receipt_apply_uid = fields.Many2one(string="发票申请人", comodel_name="res.users", tracking=True)
    receipt_apply_date = fields.Date(string="发票申请时间", tracking=True)
    tax_receipt = fields.Boolean(string="发票")
    tax_receipt_evidence = fields.Html(string="发票信息")
    tax_receipt_editable = fields.Boolean(string="发票信息可编辑",
                                          compute="_compute_tax_receipt_editable")
    receipt_done_by_uid = fields.Many2one(string="发票开具人", comodel_name="res.users", tracking=True)
    receipt_done_date = fields.Date(string="发票开具时间", tracking=True)

    def _compute_tax_receipt_editable(self):
        for record in self:
            record.tax_receipt_editable = \
                self.env.user.has_group('estate_lease_contract.contract_brokerage_invoice_manage')

    def _compute_receipt_type_editable(self):
        is_editable = self.env.user.has_group('estate.estate_group_business')
        for record in self:
            if not is_editable:
                record.receipt_type_editable = False
            else:
                if record.tax_receipt:
                    record.receipt_type_editable = False
                else:
                    record.receipt_type_editable = True

    @api.depends("tax_received", "date_received")
    def _compute_received(self):
        for record in self:
            domain = [('contract_rental_plan_rel_id', '=', record.contract_rental_plan_rel_id.id)]
            rcds = self.env["estate.lease.contract.property.tax"].search(domain)
            received_sum = 0.0

            for rcd in rcds:
                received_sum += rcd.tax_received
                if rcd.tax_received_sum != received_sum:
                    rcd.tax_received_sum = received_sum

                if record.contract_rental_plan_rel_id.property_tax_receivable:
                    tax_arrears = record.contract_rental_plan_rel_id.property_tax_receivable - rcd.tax_received_sum
                    if rcd.tax_arrears != tax_arrears:
                        rcd.tax_arrears = tax_arrears

                    # 根据本次实收和本次欠缴反算本次应收（不同于总应收）
                    if rcd.tax_receivable_this != rcd.tax_received + rcd.tax_arrears:
                        rcd.tax_receivable_this = rcd.tax_received + rcd.tax_arrears

            tax_arrears = record.contract_rental_plan_rel_id.property_tax_receivable - record.tax_received_sum
            if record.tax_arrears != tax_arrears:
                record.tax_arrears = tax_arrears
            # 根据本次实收和本次欠缴反算本次应收（不同于总应收）
            if record.tax_receivable_this != record.tax_received + record.tax_arrears:
                record.tax_receivable_this = record.tax_received + record.tax_arrears

            # 更新回到父级记录
            record.contract_rental_plan_rel_id.property_tax_amount_received = received_sum
            record.contract_rental_plan_rel_id.property_tax_amount_arrears = \
                record.contract_rental_plan_rel_id.property_tax_receivable - received_sum

    def action_apply_tax_invoice(self):
        for record in self:
            if record.tax_received < 0.01:
                raise UserError("开票金额有误！")
            if record.receipt_status != 'applied':
                record.receipt_status = 'applied'
                record.receipt_apply_uid = self.env.user.id
                record.receipt_apply_date = date.today()
                record._set_default_tax_receipt_evidence()

            if not record.receipt_type:
                record.receipt_type = 'zp'

    @api.onchange("tax_receipt")
    def _onchange_tax_receipt(self):
        if self.tax_receipt:
            self.receipt_done_by_uid = self.env.user.id
            self.receipt_done_date = date.today()
            self._set_default_tax_receipt_evidence()

    @api.depends("tax_receipt", "tax_receipt_evidence")
    def _compute_receipt_status(self):
        for record in self:
            if record.tax_receipt and record.tax_receipt_evidence:
                if record.receipt_status != 'done':
                    record.receipt_status = 'done'
                    record.receipt_done_by_uid = self.env.user.id
                    record.receipt_done_date = date.today()
            else:
                if record.receipt_status == 'done':
                    record.receipt_status = 'applied'

    def _set_default_tax_receipt_evidence(self):
        if not self.tax_receipt_evidence:
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

            self.tax_receipt_evidence = tmp_str
