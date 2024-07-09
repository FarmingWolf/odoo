# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from typing import Dict, List

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyExtend(models.Model):
    _description = "资产租赁合同租赁标的"
    _inherit = ['estate.property']

    rent_plan_id = fields.Many2one('estate.lease.contract.rental.plan', string="租金方案")
    property_rental_detail_ids = fields.One2many('estate.lease.contract.property.rental.detail', 'property_id',
                                                 string="租金明细")

    management_fee_plan_id = fields.Many2one('estate.lease.contract.property.management.fee.plan', string="物业费方案")

    business_method_id = fields.Char(string="经营性质", readonly=True, compute="_get_rent_plan_info")
    business_type_id = fields.Char(string="经营业态", readonly=True, compute="_get_rent_plan_info")
    main_category = fields.Char(string="主品类", readonly=True, compute="_get_rent_plan_info")
    billing_method = fields.Char(string='计费方式', readonly=True, compute="_get_rent_plan_info")
    billing_method_fixed_price_invisible = fields.Boolean(string="计费方式固定金额组不可见",
                                                          compute="_compute_billing_method_group_invisible")
    billing_method_percentage_invisible = fields.Boolean(string="计费方式纯抽成组不可见",
                                                         compute="_compute_billing_method_group_invisible")
    billing_method_progress_invisible = fields.Boolean(string="计费方式递增率组不可见",
                                                       compute="_compute_billing_method_group_invisible")
    billing_method_fixed_price_percentage_higher_invisible = \
        fields.Boolean(string="计费方式保底抽成取高组不可见",
                       compute="_compute_billing_method_group_invisible")

    # 物业费信息
    management_fee_name_description = fields.Char(string="方案描述", readonly=True,
                                                  compute="_get_property_management_fee_info")

    @api.onchange("rent_plan_id")
    def _onchange_rent_plan_id(self):
        self._compute_billing_method_group_invisible()
        self._compute_billing_progress_method_group_invisible()
        self._get_rent_plan_info()

    @api.onchange("management_fee_plan_id")
    def _onchange_management_fee_plan_id(self):
        self._get_property_management_fee_info()

    @api.depends("management_fee_plan_id")
    def _get_property_management_fee_info(self):
        print("_get_property_management_fee_info in")
        for record in self:
            if record.management_fee_plan_id:
                record.management_fee_name_description = record.management_fee_plan_id.name_description
            else:
                record.management_fee_name_description = ""
            print("record.management_fee_name_description={0}".format(record.management_fee_name_description))

    @api.depends("rent_plan_id")
    def _compute_billing_method_group_invisible(self):
        for record in self:

            record.billing_method_fixed_price_invisible = True
            record.billing_method_percentage_invisible = True
            record.billing_method_progress_invisible = True
            record.billing_method_fixed_price_percentage_higher_invisible = True

            if record.rent_plan_id:
                if record.rent_plan_id.billing_method == "by_fixed_price":
                    record.billing_method_fixed_price_invisible = False
                    record.billing_method_percentage_invisible = True
                    record.billing_method_progress_invisible = True
                    record.billing_method_fixed_price_percentage_higher_invisible = True
                elif record.rent_plan_id.billing_method == "by_percentage":
                    record.billing_method_fixed_price_invisible = True
                    record.billing_method_percentage_invisible = False
                    record.billing_method_progress_invisible = True
                    record.billing_method_fixed_price_percentage_higher_invisible = True
                elif record.rent_plan_id.billing_method == "by_progress":
                    record.billing_method_fixed_price_invisible = True
                    record.billing_method_percentage_invisible = True
                    record.billing_method_progress_invisible = False
                    record.billing_method_fixed_price_percentage_higher_invisible = True
                elif record.rent_plan_id.billing_method == "by_fixed_price_percentage_higher":
                    record.billing_method_fixed_price_invisible = True
                    record.billing_method_percentage_invisible = True
                    record.billing_method_progress_invisible = True
                    record.billing_method_fixed_price_percentage_higher_invisible = False
        print("billing_method_fixed_price_invisible={0}".format(record.billing_method_fixed_price_invisible))
        print("billing_method_percentage_invisible={0}".format(record.billing_method_percentage_invisible))
        print("billing_method_progress_invisible={0}".format(record.billing_method_progress_invisible))
        print("billing_method_fixed_price_percentage_higher_invisible={0}".format(
            record.billing_method_fixed_price_percentage_higher_invisible))

    billing_progress_method_id = fields.Char(string='递进方式', readonly=True, compute="_get_rent_plan_info")
    billing_progress_method_period_invisible = \
        fields.Boolean(string="递进方式按时间段递进组不可见", compute="_compute_billing_progress_method_group_invisible")
    billing_progress_method_turnover_invisible = \
        fields.Boolean(string="递进方式按营业额递进组不可见", compute="_compute_billing_progress_method_group_invisible")
    billing_progress_method_no_progress_invisible = \
        fields.Boolean(string="递进方式无递进组不可见", compute="_compute_billing_progress_method_group_invisible")

    @api.depends("rent_plan_id")
    def _compute_billing_progress_method_group_invisible(self):
        for record in self:
            record.billing_progress_method_period_invisible = True
            record.billing_progress_method_turnover_invisible = True
            record.billing_progress_method_no_progress_invisible = True
            if record.rent_plan_id:
                if record.rent_plan_id.billing_method == "by_progress":
                    if record.rent_plan_id.billing_progress_method_id == "by_period":
                        record.billing_progress_method_period_invisible = False
                        record.billing_progress_method_turnover_invisible = True
                        record.billing_progress_method_no_progress_invisible = True
                    elif record.rent_plan_id.billing_progress_method_id == "by_turnover":
                        record.billing_progress_method_period_invisible = True
                        record.billing_progress_method_turnover_invisible = False
                        record.billing_progress_method_no_progress_invisible = True
                    elif record.rent_plan_id.billing_progress_method_id == "no_progress":
                        record.billing_progress_method_period_invisible = True
                        record.billing_progress_method_turnover_invisible = True
                        record.billing_progress_method_no_progress_invisible = False
        print("billing_progress_method_period_invisible={0}".format(record.billing_progress_method_period_invisible))
        print(
            "billing_progress_method_turnover_invisible={0}".format(record.billing_progress_method_turnover_invisible))
        print("billing_progress_method_no_progress_invisible={0}".format(
            record.billing_progress_method_no_progress_invisible))

    period_percentage_id = fields.Char(string='期间段递增率详情', readonly=True, compute="_get_rent_plan_info")
    turnover_percentage_id = fields.Char(string='营业额抽成详情', readonly=True, compute="_get_rent_plan_info")
    payment_period = fields.Char(string="支付周期", readonly=True, compute="_get_rent_plan_info")
    rent_price = fields.Char(string="租金单价（元/天/㎡）", readonly=True, compute="_get_rent_plan_info")
    rent_amount_monthly_auto = fields.Char(string="自动计算月租金（元/月/㎡）", readonly=True, compute="_get_rent_plan_info",
                                           help="=租金单价（元/天/㎡）×计租面积（㎡）×365÷12")
    rent_amount_monthly_adjust = fields.Float(string="手动调整月租金（元/月/㎡）", help="可手动调整此金额，系统以此为准")
    payment_date = fields.Char(string="租金支付日", readonly=True, compute="_get_rent_plan_info")
    compensation_method = fields.Char(string='补差方式', readonly=True, compute="_get_rent_plan_info")
    compensation_period = fields.Char(string='补差周期', readonly=True, compute="_get_rent_plan_info")

    @api.depends("rent_plan_id")
    def _get_rent_plan_info(self):
        for record in self:

            if record.rent_plan_id:
                print("record.rent_plan_id.billing_method={0}".format(record.rent_plan_id.billing_method))
                print("record.rent_plan_id.billing_progress_method_id={0}".format(
                    record.rent_plan_id.billing_progress_method_id))

                record.business_method_id = dict(record.rent_plan_id._fields['business_method_id'].selection).get(
                    record.rent_plan_id.business_method_id)
                record.business_type_id = record.rent_plan_id.business_type_id.name
                record.main_category = record.rent_plan_id.main_category.name
                record.billing_method = dict(record.rent_plan_id._fields['billing_method'].selection).get(
                    record.rent_plan_id.billing_method)
                record.billing_progress_method_id = dict(
                    record.rent_plan_id._fields['billing_progress_method_id'].selection).get(
                    record.rent_plan_id.billing_progress_method_id)

                record.period_percentage_id = self._format_m2m_values(record.rent_plan_id.period_percentage_id)
                record.turnover_percentage_id = self._format_m2m_values(record.rent_plan_id.turnover_percentage_id)

                record.payment_period = dict(record.rent_plan_id._fields['payment_period'].selection).get(
                    record.rent_plan_id.payment_period)
                record.rent_price = record.rent_plan_id.rent_price
                record.rent_amount_monthly_auto = round(record.rent_plan_id.rent_price * record.rent_area * 365 / 12, 2)
                if record.rent_amount_monthly_adjust:
                    pass
                else:
                    record.rent_amount_monthly_adjust = round(
                        record.rent_plan_id.rent_price * record.rent_area * 365 / 12, 2)

                record.payment_date = dict(record.rent_plan_id._fields['payment_date'].selection).get(
                    record.rent_plan_id.payment_date)
                record.compensation_method = dict(record.rent_plan_id._fields['compensation_method'].selection).get(
                    record.rent_plan_id.compensation_method)
                record.compensation_period = dict(record.rent_plan_id._fields['compensation_period'].selection).get(
                    record.rent_plan_id.compensation_period)
            else:
                record.business_method_id = ""
                record.business_type_id = ""
                record.main_category = ""
                record.billing_method = ""
                record.billing_progress_method_id = ""
                record.period_percentage_id = ""
                record.turnover_percentage_id = ""
                record.payment_period = ""
                record.rent_price = ""
                record.rent_amount_monthly_auto = ""
                record.payment_date = ""
                record.compensation_method = ""
                record.compensation_period = ""

    @api.model
    def _format_m2m_values(self, records):

        formatted_values = []
        for record in records:
            formatted_values.append(f"{record.name}：{record.name_description}")
        return '； '.join(formatted_values)

    def action_refresh_rent_plan(self):
        for record in self:
            if record.rent_plan_id:
                self._onchange_rent_plan_id()

    def action_refresh_management_fee_plan(self):
        for record in self:
            if record.rent_plan_id:
                self._get_property_management_fee_info()

    # 自动计算资产状态（1、有效合同中的资产设置为已租；2、已租状态的资产，根据合同状态设置为租约已到期）
    def automatic_daily_calc_property_status(self):
        _logger.info("开始计算资产状态")
        current_date = fields.Date.context_today(self)

        property_ids = self.env['estate.property'].search([])
        for each_property in property_ids:
            _logger.info(f"资产{each_property.name}状态={each_property.state}")
            state_change = False
            # 本property对应的所有contract，原则上只能有一条active的contract
            current_contract = self.env['estate.lease.contract'].search([('property_ids', 'in', each_property.id),
                                                                         ('active', '=', True),
                                                                         ('state', '=', 'released')],
                                                                        order='date_rent_end DESC', limit=1)
            # 根据最新发布的合同
            if current_contract:
                if each_property.state == "sold":
                    if current_contract.date_rent_end:
                        if current_date > current_contract.date_rent_end:
                            each_property.state == "out_dated"
                            state_change = True
                else:
                    if current_contract.date_start and current_contract.date_rent_end:
                        if current_contract.date_start <= current_date <= current_contract.date_rent_end:
                            each_property.state = "sold"
                            state_change = True

            else:  # 未发布的最新合同
                unreleased_contract = self.env['estate.lease.contract'].search(
                    [('property_ids', 'in', each_property.id),
                     ('active', '=', True),
                     ('state', '!=', 'released')],
                    order='date_rent_end DESC', limit=1)
                # 只关注未发布的新合同
                if unreleased_contract:
                    if (unreleased_contract.date_start and unreleased_contract.date_start > current_date) or \
                            (unreleased_contract.date_rent_end and unreleased_contract.date_rent_end >= current_date):
                        if each_property.state not in ("offer_received", "offer_accepted"):
                            each_property.state = "offer_received"
                            state_change = True

            _logger.info(f"资产{each_property.name}状态={each_property.state},是否需要更新【{state_change}】")
            if state_change:
                each_property.write({'state': each_property.state})
