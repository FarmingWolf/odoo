# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from typing import Dict, List

from addons.utils.models.utils import Utils
from odoo import fields, models, api
from odoo.http import request

_logger = logging.getLogger(__name__)


def _set_payment_method_str(record):
    yax = f"押{'{:.2f}'.format(round(record.deposit_months, 2)).rstrip('0').rstrip('.')}"

    if record.rent_plan_id and record.rent_plan_id.payment_period:
        return f"{yax}付{record.rent_plan_id.payment_period}"
    else:
        return yax


class EstateLeaseContractPropertyExtend(models.Model):
    _description = "资产租赁合同租赁标的"
    _inherit = ['estate.property']

    def _get_default_rent_plan(self):
        # 把来自xml的action.contract_read_only写进session
        request.session["contract_read_only"] = self.env.context.get('contract_read_only')
        request.session["menu_root"] = self.env.context.get('menu_root')
        _logger.info(f"资产管理模型：session[menu_root]=【{request.session.get('menu_root')}】")
        _logger.info(f"资产管理模型：session[contract_read_only]=【{request.session.get('contract_read_only')}】")
        session_contract_id = request.session.get('session_contract_id')
        _logger.info(f"资产管理模型：session_contract_id=[{session_contract_id}]")

        for record in self:
            # 如果不是只读查看模式
            _logger.info(f"租赁标的-contract_read_only=[{request.session.get('contract_read_only')}]")
            if not request.session.get('contract_read_only'):
                record.default_rental_plan = None
                # 如果从合同录入页面过来，设置合同相关信息
                if request.session.get('menu_root') == 'estate.lease.contract' and session_contract_id:
                    contract_rcd = self.env['estate.lease.contract'].search(
                        [('id', '=', session_contract_id), ('active', '=', False)], limit=1)

                    for rcd in contract_rcd:
                        _logger.info(f"设置本资产的合同相关信息：{rcd.name}")
                        record.current_contract_no = rcd.contract_no
                        record.current_contract_nm = rcd.name
                        record.latest_rent_date_s = rcd.date_rent_start
                        record.latest_rent_date_e = rcd.date_rent_end
                        record.latest_rent_days = rcd.days_rent_total
                        record.latest_contact_person = rcd.renter_id.name
                        record.latest_contact_person_tel = rcd.renter_id.phone

                return

            # 如果session_contract_id存在，从contract_property_rental_plan_rel中查找
            rel_model = self.env['estate.lease.contract.rental.plan.rel']
            rel_rcd = rel_model.search([('contract_id', '=', session_contract_id), ('property_id', '=', record.id)],
                                       limit=1)
            if rel_rcd:
                record.default_rental_plan = rel_rcd.rental_plan_id
                record.rent_plan_id = rel_rcd.rental_plan_id
            else:
                # 不存在就是不存在，也不能拿生效合同的数据来用
                record.default_rental_plan = None
                record.rent_plan_id = None

    default_rental_plan = fields.Integer(string="根据context contract找到的租金计划", store=False,
                                         default=_get_default_rent_plan)
    # rental_plan_rel_id = fields.Many2one('estate.lease.contract.rental.plan_rel', string="租金方案关系")
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
    deposit_months = fields.Float(string="押金月数", digits=(3, 1), default=0)
    deposit_amount = fields.Float(string="押金金额", digits=(12, 2), default=0)
    # 物业费信息
    management_fee_name_description = fields.Char(string="方案描述", readonly=True,
                                                  compute="_get_property_management_fee_info")

    @api.depends("rent_amount_monthly_auto", "rent_amount_monthly_adjust", "deposit_months", "deposit_amount")
    def _cal_deposit(self):
        for record in self:
            if record.rent_amount_monthly_adjust:
                record.deposit_amount = round(record.deposit_months * record.rent_amount_monthly_adjust, 2)
                record.deposit_months = round(record.deposit_amount / record.rent_amount_monthly_adjust, 1)

            else:
                record.deposit_amount = round(record.deposit_months * record.rent_amount_monthly_auto, 2)
                if record.rent_amount_monthly_auto:
                    record.deposit_months = round(record.deposit_amount / record.rent_amount_monthly_auto, 1)
                else:
                    record.deposit_months = 0

            record.latest_payment_method = _set_payment_method_str(record)

    @api.onchange("rent_amount_monthly_adjust", "deposit_months")
    def _cal_month_2_amount_change(self):
        for record in self:
            if record.rent_amount_monthly_adjust:
                record.deposit_amount = round(record.deposit_months * record.rent_amount_monthly_adjust, 2)
            else:
                record.deposit_amount = round(record.deposit_months * record.rent_amount_monthly_auto, 2)

            record.latest_payment_method = _set_payment_method_str(record)

    @api.onchange("rent_amount_monthly_adjust", "deposit_amount")
    def _cal_amount_2_month_change(self):
        for record in self:
            if record.rent_amount_monthly_adjust:
                record.deposit_months = round(record.deposit_amount / record.rent_amount_monthly_adjust, 1)
            else:
                if record.rent_amount_monthly_auto:
                    record.deposit_months = round(record.deposit_amount / record.rent_amount_monthly_auto, 1)
                else:
                    record.deposit_months = 0

            record.latest_payment_method = _set_payment_method_str(record)

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
        for record in self:
            if record.management_fee_plan_id:
                record.management_fee_name_description = record.management_fee_plan_id.name_description
            else:
                record.management_fee_name_description = ""

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
        # print("billing_method_fixed_price_invisible={0}".format(record.billing_method_fixed_price_invisible))
        # print("billing_method_percentage_invisible={0}".format(record.billing_method_percentage_invisible))
        # print("billing_method_progress_invisible={0}".format(record.billing_method_progress_invisible))
        # print("billing_method_fixed_price_percentage_higher_invisible={0}".format(
        #     record.billing_method_fixed_price_percentage_higher_invisible))

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
        # print("billing_progress_method_period_invisible={0}".format(record.billing_progress_method_period_invisible))
        # print(
        #     "billing_progress_method_turnover_invisible={0}".format(record.billing_progress_method_turnover_invisible))
        # print("billing_progress_method_no_progress_invisible={0}".format(
        #     record.billing_progress_method_no_progress_invisible))

    period_percentage_id = fields.Char(string='期间段递增率详情', readonly=True, compute="_get_rent_plan_info")
    turnover_percentage_id = fields.Char(string='营业额抽成详情', readonly=True, compute="_get_rent_plan_info")
    payment_period = fields.Char(string="支付周期", readonly=True, compute="_get_rent_plan_info")
    rent_price = fields.Float(string="租金单价（元/天/㎡）", readonly=True, compute="_get_rent_plan_info")
    rent_amount_monthly_auto = fields.Float(string="月租金（元/月）", readonly=True, compute="_get_rent_plan_info",
                                            help="=租金单价（元/天/㎡）×计租面积（㎡）×365÷12")
    rent_amount_monthly_adjust = fields.Float(string="手调月租金（元/月）", help="可手动调整此金额。若调整后不为0，则系统以此为准。")
    payment_date = fields.Char(string="租金支付日", readonly=True, compute="_get_rent_plan_info")
    compensation_method = fields.Char(string='补差方式', readonly=True, compute="_get_rent_plan_info")
    compensation_period = fields.Char(string='补差周期', readonly=True, compute="_get_rent_plan_info")

    @api.depends("rent_plan_id")
    def _get_rent_plan_info(self):
        for record in self:

            if record.rent_plan_id:
                # print("record.rent_plan_id.billing_method={0}".format(record.rent_plan_id.billing_method))
                # print("record.rent_plan_id.billing_progress_method_id={0}".format(
                #     record.rent_plan_id.billing_progress_method_id))

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
                record.rent_price = Utils.remove_last_zero(record.rent_plan_id.rent_price)
                _logger.info(f"record.rent_price={record.rent_price}")
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
                record.latest_payment_method = _set_payment_method_str(record)

            else:
                record.business_method_id = ""
                record.business_type_id = ""
                record.main_category = ""
                record.billing_method = ""
                record.billing_progress_method_id = ""
                record.period_percentage_id = ""
                record.turnover_percentage_id = ""
                record.payment_period = 0
                record.rent_price = 0
                record.rent_amount_monthly_auto = 0
                record.payment_date = ""
                record.compensation_method = ""
                record.compensation_period = ""
                record.latest_payment_method = ""

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
