# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime
from typing import Dict, List

from addons.utils.models.utils import Utils
from odoo import fields, models, api, SUPERUSER_ID
from odoo.cli.scaffold import env
from odoo.http import request

_logger = logging.getLogger(__name__)


def _set_payment_method_str(record):
    yax = f"押{'{:.2f}'.format(round(record.deposit_months, 2)).rstrip('0').rstrip('.')}"

    if record.rent_plan_id and record.rent_plan_id.payment_period:
        return f"{yax}付{record.rent_plan_id.payment_period}"
    else:
        if record.set_rent_plan_on_this_page and record.set_rent_plan_payment_period:
            return f"{yax}付{record.set_rent_plan_payment_period}"

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
        session_contract_id = ""
        if 'session_contract_id' in request.session:
            session_contract_id = request.session.get('session_contract_id')
        _logger.info(f"资产管理模型：session_contract_id=[{session_contract_id}]")

        for record in self:
            # 如果不是只读查看模式，即编辑模式的时候，合同尚未激活
            _logger.info(f"租赁标的-contract_read_only=[{request.session.get('contract_read_only')}]")
            if not request.session.get('contract_read_only'):
                active_flg = False
            else:
                active_flg = True

            record.default_rental_plan = None
            record.rental_plan_rel_id = None
            # 如果从合同录入页面过来，设置合同相关信息
            if request.session.get('menu_root') == 'estate.lease.contract' and session_contract_id:
                # 当从合同录入界面过来时，看当前资产状态只要不是在在租，那么就把他设置为可以设置租金方案的状态

                contract_rcd = self.env['estate.lease.contract'].search([('id', '=', session_contract_id),
                                                                         ('active', '=', active_flg)], limit=1)
                for rcd in contract_rcd:
                    _logger.info(f"设置本资产的合同相关信息：{rcd.name},id:{rcd.id}")
                    record.current_contract_no = rcd.contract_no
                    record.current_contract_nm = rcd.name
                    record.latest_rent_date_s = rcd.date_rent_start
                    record.latest_rent_date_e = rcd.date_rent_end
                    record.latest_rent_days = rcd.days_rent_total
                    record.latest_contact_person = rcd.renter_id.name
                    record.latest_contact_person_tel = rcd.renter_id.phone

                # 如果session_contract_id存在，从contract_property_rental_plan_rel中查找
                rel_model = self.env['estate.lease.contract.rental.plan.rel']
                rel_rcd = rel_model.search([('contract_id', '=', session_contract_id), ('property_id', '=', record.id)],
                                           limit=1)
                for rcd in rel_rcd:
                    if rcd.rental_plan_id.id:
                        record.default_rental_plan = rcd.rental_plan_id.id
                        _logger.info(f"设置合同-资产-租金方案历史default_rental_plan={record.default_rental_plan}")
                        record.rent_plan_id = rcd.rental_plan_id.id
                        record.rental_plan_rel_id = rcd.rental_plan_id.id
                        _logger.info(f"设置合同-资产-租金方案历史rent_plan_id={record.rent_plan_id}")

    default_rental_plan = fields.Many2one('estate.lease.contract.rental.plan',
                                          string="根据context contract找到的租金计划", store=False,
                                          default=_get_default_rent_plan, compute="_get_default_rent_plan")
    # 该字段用于存储合同-资产-租金方案关系，理论上只能有一条
    rental_plan_rel_id = fields.Many2one('estate.lease.contract.rental.plan.rel', string="合同-资产-租金方案关系",
                                         default=_get_default_rent_plan, compute="_get_default_rent_plan")
    rent_plan_id = fields.Many2one('estate.lease.contract.rental.plan', string="租金方案",
                                   default=lambda self: self._get_default_rent_plan())
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
    deposit_months = fields.Float(string="押金月数", default=0)
    deposit_amount = fields.Float(string="押金金额", default=0)
    # 物业费信息
    management_fee_name_description = fields.Char(string="方案描述", readonly=True,
                                                  compute="_get_property_management_fee_info")
    # 本页面设置固定金额方案（生成新方案并保存至rental_plan）
    set_rent_plan_on_this_page = fields.Boolean(string="固定金额方案", compute="_compute_set_rent_plan_on_this_page",
                                                readonly=False, store=True, default=False)
    set_rent_plan_plan_name = fields.Char(string="固定租金方案", store=False, compute="_compute_set_rent_plan_plan_name",
                                          readonly=False)
    set_rent_plan_business_method_id = fields.Selection(string="经营性质",
                                                        selection=[('direct_sale', '直营'), ('franchisee', '加盟'),
                                                                   ('agent', '代理'), ('direct_and_agent', '直营+代理'),
                                                                   ('direct_and_franchisee', '直营+加盟')],
                                                        default='direct_sale', store=False)
    set_rent_plan_business_type_id = fields.Many2one("estate.lease.contract.rental.business.type", string="经营业态",
                                                     store=False)
    set_rent_plan_main_category = fields.Many2one("estate.lease.contract.rental.main.category", string="主品类",
                                                  store=False)
    set_rent_plan_billing_method = fields.Selection(string='计费方式', store=False,
                                                    selection=[('by_fixed_price', '固定金额'), ('by_percentage', '纯抽成'),
                                                               ('by_progress', '按递增率'),
                                                               ('by_fixed_price_percentage_higher', '保底抽成两者取高')],
                                                    default='by_fixed_price')
    set_rent_plan_payment_period = fields.Selection(string="支付周期", default='3', store=False,
                                                    selection=[('1', '月付'), ('2', '双月付'), ('3', '季付'),
                                                               ('4', '四个月付'), ('6', '半年付'), ('12', '年付')])

    set_rent_plan_payment_date = fields.Selection(string="租金支付日", default='period_start_15_bef_this', store=False,
                                                  selection=[
                                                      ('period_start_30_bef_this', '租期开始日的30日前付本期费用'),
                                                      ('period_start_15_bef_this', '租期开始日的15日前付本期费用'),
                                                      ('period_start_10_bef_this', '租期开始日的10日前付本期费用'),
                                                      ('period_start_7_bef_this', '租期开始日的7日前付本期费用'),
                                                      ('period_start_5_bef_this', '租期开始日的5日前付本期费用'),
                                                      ('period_start_1_bef_this', '租期开始日的1日前付本期费用'),
                                                      ('period_start_30_pay_this', '租期开始后的30日内付本期费用'),
                                                      ('period_start_15_pay_this', '租期开始后的15日内付本期费用'),
                                                      ('period_start_10_pay_this', '租期开始后的10日内付本期费用'),
                                                      ('period_start_7_pay_this', '租期开始后的7日内付本期费用'),
                                                      ('period_start_5_pay_this', '租期开始后的5日内付本期费用'),
                                                      ('period_start_1_pay_this', '租期开始后的1日内付本期费用'), ])
    # 这三个字段需要用store=True的方式来进一步确定“在本页设置了固定金额租金方案”
    set_rent_plan_rent_price = fields.Float(default=0.0, string="单价（元/天/㎡）",
                                            help="可设置精确到小数点后若干位，以确保月租金、年租金符合期望值")
    set_rent_plan_rent_amount_monthly_adjust = fields.Float(string="月租金（元）", default=0.0,
                                                            help="=租金单价（元/天/㎡）×计租面积（㎡）×365÷12")
    set_rent_plan_annual_rent = fields.Float(string="年租金（元）", default=0.0)

    @api.onchange("set_rent_plan_payment_period")
    def _onchange_set_rent_plan_payment_period(self):
        for record in self:
            record.latest_payment_method = _set_payment_method_str(record)

    @api.onchange("set_rent_plan_rent_price")
    def _onchange_set_rent_plan_rent_price(self):
        for record in self:
            if record.set_rent_plan_rent_price:
                record.set_rent_plan_annual_rent = record.set_rent_plan_rent_price * 365 * record.rent_area
                record.set_rent_plan_rent_amount_monthly_adjust = record.set_rent_plan_annual_rent / 12

                record._origin.set_rent_plan_rent_price = record.set_rent_plan_rent_price
                record._origin.set_rent_plan_annual_rent = record.set_rent_plan_annual_rent
                record._origin.set_rent_plan_rent_amount_monthly_adjust = record.set_rent_plan_rent_amount_monthly_adjust
            else:
                record.set_rent_plan_annual_rent = 0
                record.set_rent_plan_rent_amount_monthly_adjust = 0

            self._set_back_set_rent_plan_values()

    @api.onchange("set_rent_plan_rent_amount_monthly_adjust")
    def _onchange_set_rent_plan_rent_amount_monthly_adjust(self):
        for record in self:
            if record.set_rent_plan_rent_amount_monthly_adjust:
                record.set_rent_plan_annual_rent = record.set_rent_plan_rent_amount_monthly_adjust * 12
                record.set_rent_plan_rent_price = record.set_rent_plan_annual_rent / 365 / record.rent_area

                record._origin.set_rent_plan_rent_price = record.set_rent_plan_rent_price
                record._origin.set_rent_plan_annual_rent = record.set_rent_plan_annual_rent
                record._origin.set_rent_plan_rent_amount_monthly_adjust = record.set_rent_plan_rent_amount_monthly_adjust
            else:
                record.set_rent_plan_annual_rent = 0
                record.set_rent_plan_rent_price = 0

            self._set_back_set_rent_plan_values()

    @api.onchange("set_rent_plan_annual_rent")
    def _onchange_set_rent_plan_annual_rent(self):
        for record in self:
            if record.set_rent_plan_annual_rent:
                record.set_rent_plan_rent_amount_monthly_adjust = record.set_rent_plan_annual_rent / 12
                record.set_rent_plan_rent_price = record.set_rent_plan_annual_rent / 365 / record.rent_area

                record._origin.set_rent_plan_rent_price = record.set_rent_plan_rent_price
                record._origin.set_rent_plan_annual_rent = record.set_rent_plan_annual_rent
                record._origin.set_rent_plan_rent_amount_monthly_adjust = record.set_rent_plan_rent_amount_monthly_adjust
            else:
                record.set_rent_plan_rent_amount_monthly_adjust = 0
                record.set_rent_plan_rent_price = 0

            self._set_back_set_rent_plan_values()

    def _compute_set_rent_plan_plan_name(self):
        for record in self:
            record.set_rent_plan_plan_name = \
                str(record.name) + "-固定金额-" + \
                fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d%H%M%S')

    def _set_back_set_rent_plan_values(self):
        for record in self:
            if record.set_rent_plan_on_this_page:
                record.rent_price = record.set_rent_plan_rent_price
                record.rent_amount_monthly_auto = record.set_rent_plan_rent_amount_monthly_adjust
                record.rent_amount_monthly_adjust = record.set_rent_plan_rent_amount_monthly_adjust
                record.latest_annual_rent = record.set_rent_plan_annual_rent
                record.latest_payment_method = _set_payment_method_str(record)

    @api.onchange("set_rent_plan_on_this_page")
    def _onchange_set_rent_plan_on_this_page(self):
        for record in self:
            if record.set_rent_plan_on_this_page:
                self._compute_set_rent_plan_plan_name()
                self._onchange_set_rent_plan_rent_price()
                self._set_back_set_rent_plan_values()
            else:
                # 按照租金方案下拉框中的value
                self.action_refresh_rent_plan()

    @api.depends("rent_plan_id")
    def _compute_set_rent_plan_on_this_page(self):
        for record in self:
            if record.rent_plan_id:
                record.set_rent_plan_on_this_page = False
            else:
                record.set_rent_plan_on_this_page = True

    @api.depends("rent_amount_monthly_auto", "rent_amount_monthly_adjust", "deposit_months", "deposit_amount")
    def _cal_deposit(self):
        for record in self:
            if record.rent_amount_monthly_adjust:
                record.deposit_amount = record.deposit_months * record.rent_amount_monthly_adjust
                record.deposit_months = record.deposit_amount / record.rent_amount_monthly_adjust

            else:
                record.deposit_amount = record.deposit_months * record.rent_amount_monthly_auto
                if record.rent_amount_monthly_auto:
                    record.deposit_months = record.deposit_amount / record.rent_amount_monthly_auto
                else:
                    record.deposit_months = 0

            record.latest_payment_method = _set_payment_method_str(record)

    @api.onchange("rent_amount_monthly_adjust", "deposit_months")
    def _cal_month_2_amount_change(self):
        for record in self:
            if record.rent_amount_monthly_adjust:
                record.deposit_amount = record.deposit_months * record.rent_amount_monthly_adjust
            else:
                record.deposit_amount = record.deposit_months * record.rent_amount_monthly_auto

            record.latest_payment_method = _set_payment_method_str(record)

    @api.onchange("rent_amount_monthly_adjust", "deposit_amount")
    def _cal_amount_2_month_change(self):
        for record in self:
            if record.rent_amount_monthly_adjust:
                record.deposit_months = record.deposit_amount / record.rent_amount_monthly_adjust
            else:
                if record.rent_amount_monthly_auto:
                    record.deposit_months = record.deposit_amount / record.rent_amount_monthly_auto
                else:
                    record.deposit_months = 0

            record.latest_payment_method = _set_payment_method_str(record)

    @api.onchange("rent_amount_yearly_adjust")
    def _onchange_rent_amount_yearly_adjust(self):
        if not self.rent_amount_yearly_adjust_4_view:
            self.rent_amount_monthly_adjust = self.rent_amount_yearly_adjust / 12
        self.latest_annual_rent = self.rent_amount_yearly_adjust

    @api.onchange("rent_amount_monthly_adjust")
    def _onchange_rent_amount_monthly_adjust(self):
        if not self.rent_amount_yearly_adjust_4_view:
            self.rent_amount_yearly_adjust = self.rent_amount_monthly_adjust * 12
        self.latest_annual_rent = self.rent_amount_yearly_adjust

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
    rent_amount_monthly_auto = fields.Float(string="月租金（元）", readonly=True, compute="_get_rent_plan_info",
                                            help="=租金单价（元/天/㎡）×计租面积（㎡）×365÷12")
    rent_amount_monthly_adjust = fields.Float(string="手调月租金（元）", help="可手动调整此金额。若调整后不为0，则系统以此为准。")
    rent_amount_yearly_adjust = fields.Float(string="手调年租金（元）", help="请通过点击后方单选框明确本字段用于系统计算或仅显示。",
                                             default=lambda self: self.rent_amount_yearly_adjust * 12)
    rent_amount_yearly_adjust_4_view = fields.Boolean(string="手调年租金仅用于页面显示", default=False,
                                                      help="勾选则表示手调年租金仅用于页面显示而不参与系统自动计算；"
                                                           "不勾选则表示手调年租金不仅用于系统自动计算租金，还用于页面显示。"
                                                           "当合同约定月租金与年租金有明显较大差额时可勾选此项。")
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
                record.rent_amount_monthly_auto = record.rent_plan_id.rent_price * record.rent_area * 365 / 12
                if record.rent_amount_monthly_adjust:
                    pass
                else:
                    record.rent_amount_monthly_adjust = record.rent_plan_id.rent_price * record.rent_area * 365 / 12

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
        if 'is_from_page_click' in self.env.context and self.env.context.get('is_from_page_click') is True:
            self.env.cr.execute(f'SELECT DISTINCT company_id FROM estate_property WHERE company_id = '
                                f'{self.env.user.company_id.id}')
        else:
            self = self.with_user(SUPERUSER_ID)
            self.env.cr.execute(f'SELECT DISTINCT company_id FROM estate_property')

        property_companies = set(self.env.cr.fetchall())
        for company_id in property_companies:
            # 每日JOB从数据库里记录的最新一天开始往后按天计算
            company_domain = ('company_id', '=', company_id[0])
            property_ids = self.env['estate.property'].search([company_domain])
            _logger.info(f"自动执行job获取了公司{company_id[0]}property_ids={property_ids}")
            for each_property in property_ids:
                _logger.info(f"资产{each_property.name}状态={each_property.state}")
                state_change = False
                # 本property对应的所有contract，原则上同一期间段只能有一条active的contract，且未终止的，如果有多条，肯定是不同期间段
                current_contracts = self.env['estate.lease.contract'].search([('property_ids', 'in', each_property.id),
                                                                              ('active', '=', True),
                                                                              ('terminated', '=', False),
                                                                              ('state', '=', 'released')],
                                                                             order='date_rent_end ASC')
                # 由早到晚逐条判断
                now_in_period = False
                i = 0
                for current_contract in current_contracts:
                    i += 1
                    # 因为合同计租开始终了日都是必填字段所以不必判空
                    if current_date < current_contract.date_rent_start:
                        # 如果第一条就在当前日之后，那么后边也一定在当前日之后，所以不是最后一条的未开始不更新
                        # 如果当前日在开始日之前，而i小于len，那么说明后边还有
                        if i == len(current_contracts):
                            if each_property.state != "offer_accepted" and not now_in_period:
                                each_property.state = "offer_accepted"
                                state_change = True
                    elif current_contract.date_rent_start <= current_date <= current_contract.date_rent_end:
                        now_in_period = True  # 若当前日期正在期间内，那么这条合同状态最优先
                        if each_property.state != "sold":
                            each_property.state = "sold"
                            state_change = True
                    elif current_date > current_contract.date_rent_end:
                        # 合同状态更新为invalid=过期/失效
                        _logger.info(f"公司{each_property.company_id},"
                                     f"合同{current_contract.id}-{current_contract.name}"
                                     f"原状态=released,更新为invalid")
                        # current_contract.write({'state': 'invalid'})
                        self.env.cr.execute(f"UPDATE estate_lease_contract SET state = 'invalid' "
                                            f"WHERE id = {current_contract.id}")
                        # 若有多条合同发布，前边过期，后边也一定过期，所以不是最后一条的过期合同不用更新资产状态
                        # 如果当前日在结束日日之后，而i小于len，那么说明后边还有
                        if i == len(current_contracts):
                            if each_property.state != "out_dated":
                                each_property.state = "out_dated"
                                state_change = True
                    else:
                        _logger.error(f"不可能出现这样的错误：current_contract id={current_contract.id},"
                                      f"current_date={current_date},"
                                      f"current_contract.date_rent_start={current_contract.date_rent_start},"
                                      f"current_contract.date_rent_end={current_contract.date_rent_end}")

                # 如果上边没找到合同，那么就看已发布未生效的最新合同，且未终止的
                if i == 0:
                    unreleased_contracts = self.env['estate.lease.contract'].search(
                        [('property_ids', 'in', each_property.id),
                         ('active', '=', True),
                         ('terminated', '=', False),
                         ('state', '!=', 'released')],
                        order='date_rent_end ASC')
                    # 关注未发布的新合同和手动更新结束日期后变为失效的合同
                    now_in_period = False
                    for unreleased_contract in unreleased_contracts:
                        i += 1
                        # 未来生效的合同
                        if current_date < unreleased_contract.date_start:
                            if unreleased_contract.state != 'recording':
                                if each_property.state not in ("offer_received", "offer_accepted") and \
                                        i == len(unreleased_contract) and not now_in_period:
                                    each_property.state = "offer_accepted"
                                    state_change = True

                                if unreleased_contract.state != 'to_be_released':
                                    _logger.info(f"公司{each_property.company_id},合同{unreleased_contract.id}"
                                                 f"原状态={unreleased_contract.state},更新为to_be_released")
                                    # unreleased_contract.write({'state': 'to_be_released'})
                                    self.env.cr.execute(f"UPDATE estate_lease_contract SET state = 'to_be_released' "
                                                        f"WHERE id = {unreleased_contract.id}")

                        # 按日期，已经生效的合同：合同开始日 与 计租结束日之间
                        elif unreleased_contract.date_start <= current_date <= unreleased_contract.date_rent_end:
                            # 如果合同处于已发布待生效/已生效状态，那么可以更新合同为生效状态，资产为已租状态
                            if unreleased_contract.state != 'recording':
                                if unreleased_contract.state != 'released':
                                    _logger.info(f"公司{each_property.company_id},合同{unreleased_contract.id}"
                                                 f"原状态={unreleased_contract.state},更新为released")
                                    # unreleased_contract.write({'state': 'released'})
                                    self.env.cr.execute(f"UPDATE estate_lease_contract SET state = 'released' "
                                                        f"WHERE id = {unreleased_contract.id}")

                                # 当前在计租开始日之前
                                if current_date < unreleased_contract.date_rent_start:
                                    if each_property.state != "offer_accepted" and not now_in_period:
                                        each_property.state = "offer_accepted"
                                        state_change = True
                                elif unreleased_contract.date_rent_start <= current_date <= \
                                        unreleased_contract.date_rent_end:
                                    now_in_period = True
                                    if each_property.state != 'sold':
                                        each_property.state = "sold"
                                        state_change = True

                        elif current_date > unreleased_contract.date_rent_end:
                            if unreleased_contract.state != 'recording':
                                # 不是最后一条的过期合同不更新资产状态，如果i < len说明后边还有过期的，但后还有可能有当前日在期间内的
                                if i == len(unreleased_contracts):
                                    if each_property.state not in ("canceled", "out_dated"):
                                        each_property.state = "out_dated"
                                        state_change = True

                                if unreleased_contract.state != 'invalid':
                                    _logger.info(f"公司{each_property.company_id},合同{unreleased_contract.id}"
                                                 f"原状态={unreleased_contract.state},更新为invalid")
                                    # unreleased_contract.write({'state': 'invalid'})
                                    self.env.cr.execute(f"UPDATE estate_lease_contract SET state = 'invalid' "
                                                        f"WHERE id = {unreleased_contract.id}")
                        else:
                            _logger.error(f"不应该出现这样的错误：unreleased_contract id={unreleased_contract.id},"
                                          f"current_date={current_date},"
                                          f"unreleased_contract.date_rent_start={unreleased_contract.date_rent_start},"
                                          f"unreleased_contract.date_rent_end={unreleased_contract.date_rent_end}")

                    if i == 0:
                        # 在以上已发布的合同，未发布的合同，都没有的情况下，看已终止的合同，且上述都没有的情况下，看1个就够改的了
                        terminated_contract = self.env['estate.lease.contract'].search(
                            [('property_ids', 'in', each_property.id),
                             ('active', '=', True),
                             ('terminated', '=', True)],
                            order='date_rent_end DESC', limit=1)
                        if terminated_contract:
                            # 如果合同已终止，资产状态就不能sold
                            if each_property.state == "sold":
                                each_property.state = 'out_dated'
                                state_change = True

                _logger.info(f"公司{each_property.company_id},资产{each_property.name}状态={each_property.state},"
                             f"{'【不】' if not state_change else ''}需要更新")
                if state_change:
                    # each_property.write({'state': each_property.state})
                    self.env.cr.execute(f"UPDATE estate_property SET state = '{each_property.state}' "
                                        f"WHERE id = {each_property.id}")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        # 如果是在本页设置固定金额方案
        _logger.info(f"create vals={vals}")
        if 'set_rent_plan_on_this_page' in vals and vals['set_rent_plan_on_this_page']:
            # 租金方案写库 并 回写
            set_rent_plan_plan_name = vals['set_rent_plan_plan_name']
            if 'False' in set_rent_plan_plan_name:
                set_rent_plan_plan_name = vals['set_rent_plan_plan_name'].replace('False', vals['name'])
            rental_plan = self._set_rent_plan_on_this_page_2_db(vals, res, set_rent_plan_plan_name)
            vals['rent_plan_id'] = rental_plan.id
            _logger.info(f"create 租金方案写库 并 回写rental_plan.id={rental_plan.id}")
            res.rent_plan_id = rental_plan.id

        return res

    def write(self, vals):

        # 如果是在本页设置固定金额方案，那么一定是一个新的固定金额方案，就不应该存在重复
        _logger.info(f"write vals={vals}")

        for record in self:
            if record.set_rent_plan_on_this_page or \
                    ('set_rent_plan_on_this_page' in vals and vals['set_rent_plan_on_this_page'] is True):
                # 20240826 发现有的操作者仅仅在此修改支付周期，所以判断所有字段修改
                if ('set_rent_plan_rent_price' in vals and vals['set_rent_plan_rent_price']) or \
                        ('set_rent_plan_rent_amount_monthly_adjust' in vals and vals[
                            'set_rent_plan_rent_amount_monthly_adjust']) or \
                        ('set_rent_plan_annual_rent' in vals and vals['set_rent_plan_annual_rent']) or \
                        ('set_rent_plan_business_method_id' in vals and vals['set_rent_plan_business_method_id']) or \
                        ('set_rent_plan_business_type_id' in vals and vals['set_rent_plan_business_type_id']) or \
                        ('set_rent_plan_main_category' in vals and vals['set_rent_plan_main_category']) or \
                        ('set_rent_plan_billing_method' in vals and vals['set_rent_plan_billing_method']) or \
                        ('set_rent_plan_payment_period' in vals and vals['set_rent_plan_payment_period']) or \
                        ('set_rent_plan_payment_date' in vals and vals['set_rent_plan_payment_date']):
                    # 租金方案写库 并 回写
                    rental_plan = self._set_rent_plan_on_this_page_2_db(vals, record, record.set_rent_plan_plan_name)
                    vals['rent_plan_id'] = rental_plan.id
                    # 也回写到本Record
                    record.rent_plan_id = rental_plan.id
                    # 还要写到rental_plan_rel表
                    # 还要更新关系表estate_lease_contract_rental_plan_rel
                    rel_model = self.env['estate.lease.contract.rental.plan.rel']
                    if 'session_contract_id' in request.session:
                        session_contract_id = request.session.get('session_contract_id')
                        rel_model.search([('contract_id', '=', session_contract_id),
                                          ('property_id', '=', record.id)]).write({'rental_plan_id': rental_plan.id})
                    else:
                        _logger.info(f"session 中无key： session_contract_id ，可能来自cron的调用……")

                    # 既然已保存租金方案，则设置本页编辑开关关闭
                    vals['set_rent_plan_on_this_page'] = False

                    _logger.info(f"write vals 再做成={vals}")
            else:
                # 如果不是在本页设置固定金额模式，那也可能时在本页修改了租金方案，就要把修改后的租金方案写回关系表
                if 'rent_plan_id' in vals:
                    rel_model = self.env['estate.lease.contract.rental.plan.rel']
                    if request and request.session and 'session_contract_id' in request.session:
                        session_contract_id = request.session.get('session_contract_id')
                        rel_model.search([('contract_id', '=', session_contract_id),
                                          ('property_id', '=', record.id)]).write(
                            {'rental_plan_id': vals['rent_plan_id']})
                        _logger.info(f"rent_plan_id 写进关系表 ={vals}")
                    else:
                        _logger.info(f"session 中无key： session_contract_id ，可能来自cron的调用……")

        res = super().write(vals)
        _logger.info(f"write after vals={vals}")
        # for record in self:
        #     # 如果vals有rent_plan_id
        #     if 'rent_plan_id' in vals and vals['rent_plan_id']:
        #         rcd = self.env['estate.property'].browse(record.id).mapped('rent_plan_id')
        #         for r in rcd:
        #             if not r.id:
        #                 self.env['estate.property'].browse(record.id).write({'rent_plan_id': vals['rent_plan_id'].id})

        return res

    def _set_rent_plan_on_this_page_2_db(self, vals, record_id, plan_name):
        # 只有几个设置了缺省值的没变化就不在vals里，没缺省值的要么null要么在vals里
        if 'set_rent_plan_business_method_id' in vals:
            set_rent_plan_business_method_id = vals['set_rent_plan_business_method_id']
        else:
            set_rent_plan_business_method_id = self._origin.set_rent_plan_business_method_id

        if 'set_rent_plan_payment_period' in vals:
            set_rent_plan_payment_period = vals['set_rent_plan_payment_period']
        else:
            set_rent_plan_payment_period = self._origin.set_rent_plan_payment_period

        if 'set_rent_plan_payment_date' in vals:
            set_rent_plan_payment_date = vals['set_rent_plan_payment_date']
        else:
            set_rent_plan_payment_date = self._origin.set_rent_plan_payment_date

        if 'set_rent_plan_business_type_id' in vals:
            set_rent_plan_business_type_id = vals['set_rent_plan_business_type_id']
        else:
            set_rent_plan_business_type_id = self._origin.set_rent_plan_business_type_id

        if 'set_rent_plan_main_category' in vals:
            set_rent_plan_main_category = vals['set_rent_plan_main_category']
        else:
            set_rent_plan_main_category = self._origin.set_rent_plan_main_category

        set_rent_plan_billing_method = 'by_fixed_price'

        if 'set_rent_plan_rent_price' in vals:
            set_rent_plan_rent_price = vals['set_rent_plan_rent_price']
        else:
            set_rent_plan_rent_price = self._origin.set_rent_plan_rent_price

        rental_plan = {
            "name": plan_name,
            "rent_targets": record_id,
            "business_method_id": set_rent_plan_business_method_id,
            "business_type_id": set_rent_plan_business_type_id,
            "main_category": set_rent_plan_main_category,
            "billing_method": set_rent_plan_billing_method,
            "payment_period": set_rent_plan_payment_period,
            "payment_date": set_rent_plan_payment_date,
            "rent_price": set_rent_plan_rent_price,
            "company_id": self.env.user.company_id.id,
        }
        _logger.info(f"write 2 db rental_plan={rental_plan}")
        res = self.env['estate.lease.contract.rental.plan'].create(rental_plan)
        return res
