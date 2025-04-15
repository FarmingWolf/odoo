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


def _get_manage_fee_received_2_date_from_rcd(record):
    if record.manage_fee_received and record.period_date_from and record.period_date_to and record.manage_fee_receivable:

        if record.manage_fee_receivable > 0:
            record.days_received = record.manage_fee_received / record.manage_fee_receivable * record.days_receivable

        record.days_arrears = record.days_receivable - record.days_received
        record.manage_fee_received_2_date = record.period_date_from + timedelta(days=record.days_received - 1)
        if record.manage_fee_received_2_date > record.period_date_to:
            if record.manage_fee_received <= record.manage_fee_amount:
                record.manage_fee_received_2_date = record.period_date_to
        return record.manage_fee_received_2_date


class EstateLeaseContractPropertyManageFeeDetail(models.Model):
    _name = "estate.lease.contract.property.manage.fee.detail"
    _description = "资产租赁合同物业费明细"
    _order = "property_id, period_date_from, manage_fee_period_no"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="物业费明细", compute="_compute_detail_name", readonly=True)
    contract_id = fields.Many2one('estate.lease.contract', string="合同", ondelete="cascade", readonly=True)
    contract_state = fields.Selection(string="合同状态", related="contract_id.state")
    property_id = fields.Many2one('estate.property', string="租赁标的", ondelete="cascade", readonly=True)
    manage_fee_amount = fields.Float(default=0.0, string="本期物业费(元)", readonly=True)
    manage_fee_amount_zh = fields.Char(string="本期物业费(元)大写", compute="_cal_manage_fee_amount_zh", store=True, readonly=True)
    manage_fee_receivable = fields.Float(default=0.0, string="本期应收(元)", compute="_get_default_manage_fee_receivable",
                                         readonly=False, store=True, tracking=True)
    manage_fee_receivable_zh = fields.Char(string="本期应收(元)大写", compute="_cal_manage_fee_receivable_zh", readonly=True)
    manage_fee_received = fields.Float(default=0.0, string="本期实收(元)", tracking=True, store=True,
                                       compute="_compute_manage_fee_detail_sub_ids")
    manage_fee_received_zh = fields.Char(string="本期实收(元)大写", compute="_cal_manage_fee_received_zh", readonly=True)
    manage_fee_period_no = fields.Integer(default=0, string="期数", tracking=True)
    period_date_from = fields.Date(string="开始日期", default=lambda self: fields.Datetime.today(), tracking=True)
    period_date_to_prev = fields.Date(string="上期结束日期", compute="_get_period_date_to_prev",
                                      store=False)
    period_date_to = fields.Date(string="结束日期", default=lambda self: self._get_default_date_end(), tracking=True)
    date_payment = fields.Date(string="支付日期", tracking=True)
    description = fields.Char(string="物业费描述", readonly=True)
    active = fields.Boolean(default=True)

    renter_id = fields.Many2one('res.partner', string="承租人", related='contract_id.renter_id', readonly=True,
                                store=True, ondelete="set null")
    renter_id_phone = fields.Char(string="电话", related='contract_id.renter_id.phone', readonly=True)
    renter_id_mobile = fields.Char(string="手机", related='contract_id.renter_id.mobile', readonly=True)
    manage_fee_arrears = fields.Float(string="欠缴金额（元）", compute='_compute_manage_fee_arrears', readonly=True, store=True)
    manage_fee_arrears_zh = fields.Char(string="欠缴金额(元)大写", compute="_cal_manage_fee_arrears_zh", readonly=True)
    edited = fields.Boolean(string="有无优惠", readonly=True)
    edited_display = fields.Char(string="有优惠", compute="_get_display_edited", store=False)
    comment = fields.Text(string="修改备注")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True,
                                 ondelete="cascade")

    report_print_date = fields.Date("物业费缴费通知书打印日", store=False, compute="_get_report_print_date")
    manage_fee_received_2_date = fields.Date(string="实收至", compute="_get_manage_fee_received_2_date", readonly=True, store=True)

    period_days = fields.Integer(string="本期天数", compute="_get_period_days", readonly=True)
    incentive_days = fields.Float(string="优惠天数", default=0)
    incentive_amount = fields.Float(string="优惠金额(元)", default=0)
    days_receivable = fields.Float(string="应收天数", compute="_get_days_receivable", readonly=True)
    days_received = fields.Float(string="实收天数", compute="_get_days_received", readonly=True)
    days_arrears = fields.Float(string="欠缴天数", compute="_get_days_received", readonly=True)

    manage_fee_detail_sub_ids = fields.One2many(comodel_name="estate.lease.contract.property.fee.maintenance",
                                                inverse_name="manage_fee_detail_id", string="分次缴费明细")
    button_icon_invisible = fields.Boolean(string="切换操作按钮", default=True)
    # 合同发布生效之前，不允许编辑物业费明细的实收明细
    manage_fee_detail_sub_ids_editable = fields.Boolean("可编辑物业费实收", default=False,
                                                        compute="_compute_manage_fee_detail_sub_ids_editable")

    @api.depends('contract_id')
    def _compute_manage_fee_detail_sub_ids_editable(self):
        for record in self:
            if not record.contract_id:
                record.manage_fee_detail_sub_ids_editable = False
            else:
                if record.contract_id.state not in ['to_be_released', 'released']:
                    record.manage_fee_detail_sub_ids_editable = False
                else:
                    record.manage_fee_detail_sub_ids_editable = True

    def action_show_button_icons(self):
        for record in self:
            if record.button_icon_invisible:
                record.button_icon_invisible = False
            else:
                record.button_icon_invisible = True

    @api.depends("property_id", "contract_id", "manage_fee_period_no", "period_date_from", "period_date_to")
    def _compute_detail_name(self):
        for record in self:
            record.name = str(record.contract_id.name) + "-" + str(record.property_id.name) + "-" + \
                          record.period_date_from.strftime('%Y%m%d') + "-" + \
                          record.period_date_to.strftime('%Y%m%d') + "-" + str(record.manage_fee_period_no)

    @api.onchange("manage_fee_detail_sub_ids")
    def _onchange_manage_fee_detail_sub_ids(self):
        received_subtotal = 0
        for rcd in self.manage_fee_detail_sub_ids:
            received_subtotal += rcd.maintenance_received
        if self.manage_fee_received != received_subtotal:
            self.manage_fee_received = received_subtotal

    @api.depends("manage_fee_detail_sub_ids")
    def _compute_manage_fee_detail_sub_ids(self):
        received_subtotal = 0
        for record in self:
            for rcd in record.manage_fee_detail_sub_ids:
                received_subtotal += rcd.maintenance_received
            if record.manage_fee_received != received_subtotal:
                record.manage_fee_received = received_subtotal

    @api.onchange("period_days")
    def _onchange_period_days(self):
        # 不能直接修改优惠日期，因为可能把已经修改的优惠金额改成整期物业费，如果已经存在修改的优惠金额，那么应该根据金额来反算优惠天数
        # if self.incentive_days > self.period_days:
        #     self.incentive_days = self.period_days
        self._onchange_incentive_amount()
        self._onchange_manage_fee_receivable()
        self._onchange_manage_fee_received()

    @api.depends("incentive_days", "period_days")
    def _get_days_receivable(self):
        for record in self:
            record.days_receivable = record.period_days - record.incentive_days

    @api.depends("incentive_days", "period_days", "manage_fee_received", "incentive_amount")
    def _get_days_received(self):
        for record in self:
            record.days_received = 0
            if record.manage_fee_receivable != 0:
                record.days_received = record.manage_fee_received / record.manage_fee_receivable * record.days_receivable

            record.days_arrears = record.days_receivable - record.days_received

    @api.depends("period_date_from", "period_date_to")
    def _get_period_days(self):
        for record in self:
            if record.period_date_to and record.period_date_from:
                record.period_days = (record.period_date_to - record.period_date_from + timedelta(days=1)).days
            else:
                record.period_days = 0

    @api.depends("manage_fee_received")
    def _get_manage_fee_received_2_date(self):
        for record in self:
            record.manage_fee_received_2_date = _get_manage_fee_received_2_date_from_rcd(record)

    @api.depends("contract_id")
    def _get_report_print_date(self):
        for record in self:
            record.report_print_date = fields.Date.context_today(self)

    @api.depends("period_date_from")
    def _get_period_date_to_prev(self):
        for record in self:
            record.period_date_to_prev = record.period_date_from + timedelta(-1)

    @api.depends("edited")
    def _get_display_edited(self):
        for record in self:
            if record.edited:
                record.edited_display = "有优惠"
            else:
                record.edited_display = ""

    @api.depends("manage_fee_amount")
    def _cal_manage_fee_amount_zh(self):
        for record in self:
            record.manage_fee_amount_zh = Utils.arabic_to_chinese(round(record.manage_fee_amount, 2))

    @api.depends("manage_fee_receivable")
    def _cal_manage_fee_receivable_zh(self):
        for record in self:
            record.manage_fee_receivable_zh = Utils.arabic_to_chinese(round(record.manage_fee_receivable, 2))

    @api.depends("manage_fee_received")
    def _cal_manage_fee_received_zh(self):
        for record in self:
            record.manage_fee_received_zh = Utils.arabic_to_chinese(round(record.manage_fee_received, 2))

    @api.depends("manage_fee_arrears")
    def _cal_manage_fee_arrears_zh(self):
        for record in self:
            record.manage_fee_arrears_zh = Utils.arabic_to_chinese(round(record.manage_fee_arrears, 2))

    @api.depends("manage_fee_receivable", "manage_fee_received", "incentive_amount", "incentive_days")
    def _compute_manage_fee_arrears(self):
        for record in self:
            record.manage_fee_arrears = record.manage_fee_receivable - record.manage_fee_received

    @api.depends("manage_fee_amount", "incentive_amount", "incentive_days")
    def _get_default_manage_fee_receivable(self):
        for record in self:
            record.manage_fee_receivable = record.manage_fee_amount - record.incentive_amount

    @api.depends("period_date_from")
    def _get_default_date_end(self):
        for record in self:
            if not record.period_date_to:
                record.period_date_to = estate_lease_contract._get_current_e(record.period_date_from)
                return record.period_date_to

    @api.model
    def write(self, vals):
        _logger.info(f"vals={vals}")
        # 金额、日期几个关键字段被修改则被认为执行了优惠
        # 获取旧值
        old_values = self.read(list(vals.keys()))
        # 比较新旧值
        for i, record in enumerate(self):
            old_record_values = old_values[i]
            for field_name, new_val in vals.items():
                old_val = old_record_values[field_name]
                # 本期物业费、本期应收、本期开始结束日期、支付日期、本期优惠天数和本期优惠金额的调整，视为优惠，必须填写备注
                if old_val != new_val:
                    if field_name in ['manage_fee_amount', 'manage_fee_receivable', 'date_payment',
                                      'period_date_from', 'period_date_to', 'incentive_days', 'incentive_amount']:
                        vals['edited'] = True
                        if 'comment' in vals:
                            if vals['comment']:
                                break
                            else:
                                raise UserError('本期物业费、本期应收、本期开始结束日期、支付日期的调整，'
                                                '视为优惠。修改这些字段必须填写备注！')
                        else:
                            _logger.info(f"record.comment={record.comment}")
                            if record.comment:  # 姑且认为已经有了comment就不用再写了 todo
                                break
                            else:
                                raise UserError('本期物业费、本期应收、本期开始结束日期、支付日期、本期优惠天数、本期优惠金额的调整，'
                                                '视为优惠。修改这些字段必须填写备注！')

        res = super().write(vals)
        return res

    @api.model
    def create(self, vals_list):
        _logger.info(f"vals_list={vals_list}")
        res = super().create(vals_list)

        return res

    def action_print_payment_notice(self):
        return self.env.ref('estate_lease_contract.action_print_payment_notice').report_action(self)

    def action_round(self):
        for record in self:
            round_method = self.env.context.get('round_method')
            method_msg = self.env.context.get('method_msg')
            # amount_bef = record.manage_fee_amount
            receivable_bef = record.manage_fee_receivable
            if round_method:
                if round_method == "up2ten":
                    # amount_aft = ceil(record.manage_fee_amount / 10) * 10
                    receivable_aft = ceil(record.manage_fee_receivable / 10) * 10
                elif round_method == "round2ten":
                    # amount_aft = round(record.manage_fee_amount / 10) * 10
                    receivable_aft = round(record.manage_fee_receivable / 10) * 10
                elif round_method == "down2ten":
                    # amount_aft = floor(record.manage_fee_amount / 10) * 10
                    receivable_aft = floor(record.manage_fee_receivable / 10) * 10
                elif round_method == "up2one":
                    # amount_aft = ceil(record.manage_fee_amount)
                    receivable_aft = ceil(record.manage_fee_receivable)
                elif round_method == "round2one":
                    # amount_aft = round(record.manage_fee_amount)
                    receivable_aft = round(record.manage_fee_receivable)
                elif round_method == "down2one":
                    # amount_aft = floor(record.manage_fee_amount)
                    receivable_aft = floor(record.manage_fee_receivable)
                elif round_method == "up2hundred":
                    # amount_aft = ceil(record.manage_fee_amount / 100) * 100
                    receivable_aft = ceil(record.manage_fee_receivable / 100) * 100
                elif round_method == "round2hundred":
                    # amount_aft = round(record.manage_fee_amount / 100) * 100
                    receivable_aft = round(record.manage_fee_receivable / 100) * 100
                elif round_method == "down2hundred":
                    # amount_aft = floor(record.manage_fee_amount / 100) * 100
                    receivable_aft = floor(record.manage_fee_receivable / 100) * 100
                else:
                    _logger.error("原则上不会出现这样的错误。")
                    # amount_aft = "未知修改"
                    receivable_aft = "未知修改"

                msg = f"{fields.Date.context_today(record)}{method_msg}," \
                      f"本期应收[{round(receivable_bef, 2)}]→[{round(receivable_aft, 2)}]。"
                record.comment = msg if not record.comment else msg + record.comment
                # record.manage_fee_amount = amount_aft
                record.manage_fee_receivable = receivable_aft
                self._onchange_manage_fee_receivable()
                record.edited = True

            else:
                _logger.error("原则上也不会出现这样的错误。")

    @api.onchange("period_date_from")
    def _onchange_period_date_from(self):
        origin_val = self._origin.period_date_from if self._origin else "原始值请手动记录"
        if origin_val != self.period_date_from:
            msg = f"{fields.Date.context_today(self)}修改租期开始日[{origin_val}]→[{self.period_date_from}]。"
            self.comment = msg if not self.comment else msg + self.comment

    @api.onchange("period_date_to")
    def _onchange_period_date_to(self):
        origin_val = self._origin.period_date_to if self._origin else "原始值请手动记录"
        if origin_val != self.period_date_to:
            msg = f"{fields.Date.context_today(self)}修改租期结束日[{origin_val}]→[{self.period_date_to}]。"
            self.comment = msg if not self.comment else msg + self.comment

    @api.onchange("date_payment")
    def _onchange_date_payment(self):
        origin_val = self._origin.date_payment if self._origin else "原始值请手动记录"
        if origin_val != self.date_payment:
            msg = f"{fields.Date.context_today(self)}修改支付日期[{origin_val}]→[{self.date_payment}]。"
            self.comment = msg if not self.comment else msg + self.comment

    @api.onchange("manage_fee_amount")
    def _onchange_manage_fee_amount(self):
        origin_val = self._origin.manage_fee_amount if self._origin else "原始值请手动记录"
        if origin_val != self.manage_fee_amount:
            msg = f"{fields.Date.context_today(self)}" \
                  f"修改本期物业费[{round(origin_val, 2) if isinstance(origin_val, float) else origin_val}]" \
                  f"→[{round(self.manage_fee_amount, 2)}]。"
            self.comment = msg if not self.comment else msg + self.comment

    @api.onchange("manage_fee_receivable")
    def _onchange_manage_fee_receivable(self):
        self.incentive_amount = self.manage_fee_amount - self.manage_fee_receivable
        origin_val = self._origin.manage_fee_receivable if self._origin else "原始值请手动记录"
        if origin_val != self.manage_fee_receivable:
            msg = f"{fields.Date.context_today(self)}" \
                  f"修改本期应收[{round(origin_val, 2) if isinstance(origin_val, float) else origin_val}]→" \
                  f"[{round(self.manage_fee_receivable, 2)}]。"
            self.comment = msg if not self.comment else msg + self.comment

    @api.onchange("manage_fee_received")
    def _onchange_manage_fee_received(self):
        origin_val = self._origin.manage_fee_received if self._origin else "原始值请手动记录"
        if origin_val != self.manage_fee_received:
            msg = f"{fields.Date.context_today(self)}" \
                  f"修改本期实收[{round(origin_val, 2) if isinstance(origin_val, float) else origin_val}]→" \
                  f"[{round(self.manage_fee_received, 2)}]。"
            self.comment = msg if not self.comment else msg + self.comment

        self.manage_fee_received_2_date = _get_manage_fee_received_2_date_from_rcd(self)
        if self.manage_fee_receivable > 0:
            self.days_received = self.manage_fee_received / self.manage_fee_receivable * self.days_receivable

    @api.onchange("incentive_days")
    def _onchange_incentive_days(self):
        if self.incentive_days > self.period_days:
            self.incentive_days = self.period_days

        self.days_receivable = self.period_days - self.incentive_days
        if self.period_days > 0:
            self.incentive_amount = self.incentive_days / self.period_days * self.manage_fee_amount
        if self.manage_fee_receivable != 0:
            self.days_received = self.manage_fee_received / self.manage_fee_receivable * self.days_receivable
        self.days_arrears = self.days_receivable - self.days_received

        origin_val = self._origin.incentive_days if self._origin else "原始值请手动记录"
        if origin_val != self.incentive_days:
            msg = f"{fields.Date.context_today(self)}" \
                  f"修改本期优惠天数[{round(origin_val, 0) if isinstance(origin_val, float) else origin_val}]→" \
                  f"[{round(self.incentive_days, 0)}]。"
            self.comment = msg if not self.comment else msg + self.comment

    @api.onchange("incentive_amount")
    def _onchange_incentive_amount(self):
        if self.incentive_amount > self.manage_fee_amount:
            self.incentive_amount = self.manage_fee_amount

        if self.manage_fee_amount != 0:
            self.incentive_days = self.incentive_amount / self.manage_fee_amount * self.period_days
        self.days_receivable = self.period_days - self.incentive_days
        if self.manage_fee_receivable != 0:
            self.days_received = self.manage_fee_received / self.manage_fee_receivable * self.days_receivable
        self.days_arrears = self.days_receivable - self.days_received

        origin_val = self._origin.incentive_amount if self._origin else "原始值请手动记录"
        if origin_val != self.incentive_amount:
            msg = f"{fields.Date.context_today(self)}" \
                  f"修改本期优惠金额[{round(origin_val, 2) if isinstance(origin_val, float) else origin_val}]→" \
                  f"[{round(self.incentive_amount, 2)}]。"
            self.comment = msg if not self.comment else msg + self.comment

    def action_confirm_received(self):
        _logger.info(f"点击收齐物业费小手icon")
        for record in self:
            # 防止空点
            if abs(record.manage_fee_receivable - record.manage_fee_received) < 0.01:
                continue

            received_bef = record.manage_fee_received
            received_aft = record.manage_fee_receivable

            msg = f"{fields.Date.context_today(self)}本期物业费收齐[{round(received_bef, 2)}]→[{round(received_aft, 2)}]。"
            record.comment = msg if not record.comment else msg + record.comment
            record.manage_fee_received = received_aft
            record.edited = True
            # 增加相应的分次收缴明细
            manage_fee_detail_sub = [{
                "manage_fee_detail_id": record.id,
                "maintenance_received": received_aft - received_bef,
                # 一次收齐时，本实收记录的“应收”仍为父记录物业费明细期间总应收
                "maintenance_receivable": record.manage_fee_receivable,
                "period_d_start": record.period_date_from,
                "period_d_end": record.period_date_to,
            }]
            self.env["estate.lease.contract.property.fee.maintenance"].create(manage_fee_detail_sub)
