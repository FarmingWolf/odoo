# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta, datetime, date
from typing import Dict, List

from odoo.http import request
from odoo.tools.translate import _

from dateutil.utils import today

from addons.utils.models.utils import Utils
from odoo import fields, models, api, exceptions
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


def _cal_date_payment(current_s, current_e, rental_plan, date_e):
    """rental_plan.payment_date:[
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
    ('period_start_1_pay_this', '租期开始后的1日内付本期费用'),
    """
    if 'start' in rental_plan.payment_date:
        day_cnt = int(rental_plan.payment_date.split('_')[2])
        if 'bef' in rental_plan.payment_date:
            date_payment = current_s - timedelta(days=day_cnt)
        else:
            date_payment = current_s + timedelta(days=day_cnt)
    elif 'end' in rental_plan.payment_date:
        day_cnt = int(rental_plan.payment_date.split('_')[3])
        date_payment = current_e - timedelta(days=day_cnt)

    if 'next' in rental_plan.payment_date:
        if current_e == date_e:
            date_payment = False

    return date_payment


# 最后一期有可能不是一整期
def _cal_last_period_rental(month_cnt, current_s, current_e, date_s, date_e, property_id, rent_price_adapt,
                            rent_amount_monthly_adapt):
    last_period_rental = 0.0
    current_tmp = _get_current_e(current_s)

    # 以手调月租为准
    if property_id.rent_amount_monthly_adjust:
        rent_price_adapt = rent_amount_monthly_adapt * 12 / 365 / property_id.rent_area

    # 最后一期不足一个月，则按天算
    if current_e < current_tmp:
        period_days = current_e - current_s
        last_period_rental = property_id.rent_area * rent_price_adapt * (period_days.days + 1)
        return last_period_rental

    # 如果足月，则直接取月金额
    while current_tmp < current_e:
        if property_id.rent_amount_monthly_adjust:
            last_period_rental += rent_amount_monthly_adapt
        else:
            last_period_rental += property_id.rent_area * rent_price_adapt * 365 / 12
        current_s = current_tmp + timedelta(days=1)
        current_tmp = _get_current_e(current_s)

    # 最后不足月的天数
    if current_tmp > current_e:
        if date_e.day == date_s.day - 1:
            if property_id.rent_amount_monthly_adjust:
                last_period_rental += rent_amount_monthly_adapt
            else:
                last_period_rental += property_id.rent_area * rent_price_adapt * 365 / 12
        else:
            period_days = current_e - current_s
            last_period_rental += property_id.rent_area * rent_price_adapt * (period_days.days + 1)
    else:
        if property_id.rent_amount_monthly_adjust:
            last_period_rental += rent_amount_monthly_adapt
        else:
            last_period_rental += property_id.rent_area * rent_price_adapt * 365 / 12

    return last_period_rental


def _cal_rental_amount(month_cnt, current_s, current_e, date_s, date_e, property_id, rent_price_adapt,
                       rent_amount_monthly_adapt):
    """
    租金计算方法：先计算年租金，再计算每月租金或每期租金
    年租金=租金单价×计租面积×365
    月租金=年租金÷12
    两个月租金=月租金×2
    三个月租金=月租金×3
    以此类推
    """
    # rental_amount_year = property_id.rent_area * rent_price_val * 365
    # rental_amount_month = rental_amount_year / 12

    # if property_id.rent_amount_monthly_adjust:
    #     rental_amount_month = property_id.rent_amount_monthly_adjust
    rental_amount_month = rent_amount_monthly_adapt

    if date_e > current_e:
        rental_amount = rental_amount_month * month_cnt
    else:  # 最后一期租金
        rental_amount = _cal_last_period_rental(month_cnt, current_s, current_e, date_s, date_e, property_id,
                                                rent_price_adapt, rent_amount_monthly_adapt)

    return round(rental_amount, 2)


def _get_current_e(current_tmp):
    if current_tmp.day == 1:  # 本月1号至月末
        current_e = (current_tmp.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    elif current_tmp.day <= 29:  # 本月N号至下月N-1号
        current_e = (current_tmp.replace(day=28) + timedelta(days=4)).replace(day=current_tmp.day - 1)
    else:  # 30或者31日
        if current_tmp.month != 1:  # 当前月不是1月，下个月就不是2月，下个月的月末就都可以N-1号
            current_e = (current_tmp.replace(day=28) + timedelta(days=4)).replace(day=current_tmp.day - 1)
        else:  # 当前月是1月30、31，下个月就是2月，2月的月末必须是3月1号-1天
            current_e = (current_tmp.replace(month=3)).replace(day=1) - timedelta(days=1)

    return current_e


def _cal_rent_price_and_amount_monthly_val(current_s, rent_price_period_lst):
    for rent_price_period in rent_price_period_lst:
        if rent_price_period.get('period_from') <= current_s <= rent_price_period.get('period_to'):
            _logger.info(
                f"当前日期：{current_s}，"
                f"租金适配{rent_price_period.get('rent_amount_adapt')}, "
                f"适配单价{rent_price_period.get('rent_price_adapt')}")
            return rent_price_period.get('rent_amount_adapt'), rent_price_period.get('rent_price_adapt')
    raise UserWarning(f'租金适配期间出错：当前日期：{current_s}，租金适配表{rent_price_period_lst}')


def _prepare_rent_price_period_lst(property_id, rent_amount_monthly_val, rental_plan, record_self):
    """
    根据租金方案、计租开始日、计租结束日计算各期间的适配租金
    [
        {资产ID, 基础月租金, 基础单价, 计费方式, 递进方式, 从第N月起, 每X个月, 递增百分比,
        适配后月租金, 适配后单价, 期间开始日期, 期间结束日期}
    ]
    """
    # 默认固定金额的方式
    rtn_lst = [{'property_id': property_id,
                'rent_amount_monthly_val': rent_amount_monthly_val,
                'rent_price_val': rental_plan.rent_price,
                'billing_method': rental_plan.billing_method,
                'progress_method': False, 'from_n_month': False, 'every_x_month': False, 'up_percentage': 0,
                'rent_amount_adapt': rent_amount_monthly_val,
                'rent_price_adapt': rental_plan.rent_price,
                'period_from': record_self.date_rent_start,
                'period_to': record_self.date_rent_end}]
    _logger.info(f'先设置默认的固定金额模式={rtn_lst}')
    if rental_plan.billing_method == 'by_fixed_price':
        return rtn_lst
    elif rental_plan.billing_method == 'by_progress':
        if rental_plan.billing_progress_method_id == 'by_period':
            if not rental_plan.period_percentage_id:
                return rtn_lst

            rtn_lst = []

            for i in range(len(rental_plan.period_percentage_id)):
                period_percentage = rental_plan.period_percentage_id[i]

                if i == 0:
                    # 从开始日到”第N月“之间，还是初始利率

                    temp_date_e = _get_period_total_e(record_self.date_rent_start,
                                                      period_percentage.billing_progress_info_month_from - 1,
                                                      record_self.date_rent_end)
                    period_data = {
                        'property_id': property_id,
                        'rent_amount_monthly_val': rent_amount_monthly_val,
                        'rent_price_val': rental_plan.rent_price,
                        'billing_method': rental_plan.billing_method,
                        'progress_method': rental_plan.billing_progress_method_id,
                        'from_n_month': period_percentage.billing_progress_info_month_from,
                        'every_x_month': period_percentage.billing_progress_info_month_every,
                        'up_percentage': period_percentage.billing_progress_info_up_percentage,
                        'rent_amount_adapt': rent_amount_monthly_val,
                        'rent_price_adapt': rental_plan.rent_price,
                        'period_from': record_self.date_rent_start,
                        'period_to': temp_date_e}
                    _logger.info(f"第一个无增期间={period_data}")
                    rtn_lst.append(period_data)
                    _logger.info(f"第一个无增期间lst={rtn_lst}")
                    if temp_date_e >= record_self.date_rent_end:
                        return rtn_lst

                # 这才开始进入第一条递增期间
                temp_date_s = temp_date_e + timedelta(days=1)

                next_date_s_or_total_end = record_self.date_rent_end

                next_date_s = next_date_s_or_total_end + timedelta(days=1)  # 这只是虚拟值，最后一行才用得上
                # 看看有没有下一条递增率规则
                if i < len(rental_plan.period_percentage_id) - 1:
                    next_period_percentage = rental_plan.period_percentage_id[i + 1]
                    # 下一条规则的开始日
                    next_date_s = _get_period_total_e(record_self.date_rent_start,
                                                      next_period_percentage.billing_progress_info_month_from - 1,
                                                      record_self.date_rent_end) + timedelta(days=1)
                    next_date_s_or_total_end = min(record_self.date_rent_end, next_date_s)

                while temp_date_s < next_date_s_or_total_end:
                    # 本条规则的结束日的最大值
                    this_period_e_max = min(record_self.date_rent_end, next_date_s - timedelta(days=1))

                    temp_date_e = _get_period_total_e(temp_date_s,
                                                      period_percentage.billing_progress_info_month_every,
                                                      this_period_e_max)
                    # 上一条的适配后租金是本条的基础租金
                    base_rent_amount_monthly_val = rtn_lst[len(rtn_lst) - 1].get('rent_amount_adapt')
                    base_rent_price = rtn_lst[len(rtn_lst) - 1].get('rent_price_adapt')
                    period_data = {'property_id': property_id,
                                   'rent_amount_monthly_val': base_rent_amount_monthly_val,
                                   'rent_price_val': base_rent_price,
                                   'billing_method': rental_plan.billing_method,
                                   'progress_method': rental_plan.billing_progress_method_id,
                                   'from_n_month': period_percentage.billing_progress_info_month_from,
                                   'every_x_month': period_percentage.billing_progress_info_month_every,
                                   'up_percentage': period_percentage.billing_progress_info_up_percentage,
                                   'rent_amount_adapt': round(base_rent_amount_monthly_val * (
                                           1 + (period_percentage.billing_progress_info_up_percentage / 100)), 2),
                                   'rent_price_adapt': round(base_rent_price * (
                                           1 + (period_percentage.billing_progress_info_up_percentage / 100)), 2),
                                   'period_from': temp_date_s,
                                   'period_to': temp_date_e}

                    rtn_lst.append(period_data)
                    temp_date_s = temp_date_e + timedelta(days=1)

        return rtn_lst  # todo 非期间段递增的情况，也按照固定金额走

    else:  # todo 其他情况暂且按照固定金额走
        return rtn_lst


def _get_period_total_e(current_s, month_cnt, date_e):
    current_tmp = current_s
    for i in range(month_cnt):
        current_e = _get_current_e(current_tmp)
        current_tmp = current_e + timedelta(days=1)

    # 循环后，再调整结束日期的日至开始日期的日-1
    if current_s.day == 1:  # 1号开始的期间，按照上述逻辑，最后的current_e就是月末，不用调整
        pass
    elif current_s.day <= 29:  # 开始月的日期为29号以下，那么结束月的日子应该是28号
        current_e = current_e.replace(day=current_s.day - 1)
    else:  # 开始日期的日为30或者31日
        if current_e.month != 2:  # 结束日期不是在2月，那么其结束日期可以是N-1
            current_e = current_e.replace(day=current_s.day - 1)
        else:  # 结束日期在2月，那么上边逻辑已经计算好了2月末的最后一天小于30、31
            pass

    if current_e > date_e:
        current_e = date_e

    return current_e


def _generate_details_from_rent_plan(record_self):
    """
    一个租赁标的有一个租金方案，
    一个租金方案生成多条租金明细
    租赁期间→支付周期→支付日类型→支付日期→期数→计费方式（固定？抽成？递增？取高？）→每期支付金额
    """
    # 前边已经判断过，这里不用重复判断self
    # 根据租赁期间、支付周期、支付日期类型生成支付期
    rental_periods_details = []
    date_s = fields.Date.from_string(record_self.date_rent_start)
    date_e = fields.Date.from_string(record_self.date_rent_end)

    # 根据property去找rental_plan
    temp_rent_amount = 0.0
    temp_deposit_amount = 0.0
    for property_id in record_self.property_ids:
        if property_id.rent_plan_id:
            rental_plan = property_id.rent_plan_id
        else:
            continue

        # 20240808 之前 这里仅对固定金额的月租金进行累加并显示，完整的逻辑应该根据租金方案逐条计算
        # 20240808 增加按期间段递增率的计算，其他分支 todo
        if property_id.rent_amount_monthly_adjust:
            rent_amount_monthly_val = property_id.rent_amount_monthly_adjust
        else:
            rent_amount_monthly_val = round(rental_plan.rent_price * property_id.rent_area * 365 / 12, 2)

        temp_deposit_amount += property_id.deposit_amount if property_id.deposit_amount else 0

        month_cnt = int(rental_plan.payment_period) if rental_plan.payment_period else 1

        # 预备出当前资产的租金方案的租金适配期间
        rent_price_period_lst = _prepare_rent_price_period_lst(property_id, rent_amount_monthly_val, rental_plan,
                                                               record_self)
        _logger.info(f"rent_price_period_lst={rent_price_period_lst}")

        current_s = date_s
        period_no = 1
        while current_s <= date_e:
            # 计算本期结束日
            current_e = _get_period_total_e(current_s, month_cnt, date_e)

            rent_amount_monthly_adapt, rent_price_adapt = _cal_rent_price_and_amount_monthly_val(current_s,
                                                                                                 rent_price_period_lst)
            _logger.info(f"{period_no}期-月租={rent_amount_monthly_adapt}，单价={rent_price_adapt}")
            # 计算支付日期
            date_payment = _cal_date_payment(current_s, current_e, rental_plan, date_e)
            billing_method_str = dict(rental_plan._fields['billing_method'].selection).get(rental_plan.billing_method)
            payment_date_str = dict(rental_plan._fields['payment_date'].selection).get(rental_plan.payment_date)
            rental_amount = _cal_rental_amount(month_cnt, current_s, current_e, date_s, date_e, property_id,
                                               rent_price_adapt, rent_amount_monthly_adapt)
            rental_amount_zh = Utils.arabic_to_chinese(rental_amount)

            rental_periods_details.append({
                'contract_id': f"{record_self.id}",
                'property_id': f"{property_id.id}",
                'period_date_from': f"{current_s.strftime('%Y-%m-%d')}",
                'period_date_to': f"{current_e.strftime('%Y-%m-%d')}",
                'date_payment': date_payment,
                'rental_amount': f"{rental_amount}",
                'rental_receivable': f"{rental_amount}",  # 创建时，应收=租金计算值
                'rental_amount_zh': f"{rental_amount_zh}",
                'rental_period_no': f"{period_no}",
                'description': f"{rental_plan.name}-{billing_method_str}-{property_id.latest_payment_method}-"
                               f"{payment_date_str}",
                'active': f"{True}",
            })

            # 下期开始日
            current_s = current_e + timedelta(days=1)
            period_no += 1

        temp_rent_amount += rent_amount_monthly_val  # 这里还是显示基础月租
        print("{1}.rental_periods={0}".format(rental_periods_details, rental_plan.name))
        _logger.info(f"temp_rent_amount={temp_rent_amount}")

    record_self.rent_amount = temp_rent_amount
    record_self.rent_amount_year = temp_rent_amount * 12
    record_self.lease_deposit = temp_deposit_amount

    return rental_periods_details


class EstateLeaseContract(models.Model):
    # def onchange(self, values, field_names, fields_spec):
    #     super().onchange(values, field_names, fields_spec)

    _name = "estate.lease.contract"
    _description = "资产租赁合同管理模型"
    _order = "sequence"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    name = fields.Char('合同名称', required=True, translate=True, copy=True, default="491空间房屋租赁合同")

    contract_no = fields.Char('合同编号', required=True, translate=True, copy=False, default="")
    # contract_amount = fields.Float("合同金额", default=0.0)
    # contract_tax = fields.Float("税额", default=0.0)
    # contract_tax_per = fields.Float("税率", default=0.0)
    # contract_tax_out = fields.Float("不含税合同额", default=0.0)

    date_sign = fields.Date("合同签订日期", required=True, copy=False, default=fields.Date.context_today)
    date_start = fields.Date("合同开始日期", required=True, copy=False, default=fields.Date.context_today)

    date_rent_start = fields.Date("计租开始日期", required=True, copy=False, tracking=True, default=fields.Date.context_today)
    date_rent_end = fields.Date("计租结束日期", required=True, copy=False, tracking=True, default=fields.Date.context_today)

    days_rent_total = fields.Char(string="租赁期限", compute="_calc_days_rent_total")

    """
    rental_plans_for_property 貌似在哪都没用到
    def _compute_rental_plans_for_property(self):
        print("进入_compute_rental_plans_for_property")
        print(f"self.env.context.get('active_id')={self.env.context.get('active_id')}")
        print(f"self.env.context.get('contract_read_only')={self.env.context.get('contract_read_only')}")
        print(f"self.env.context.get('context_contract_id')={self.env.context.get('context_contract_id')}")
        for contract in self:
            contract.rental_plans_for_property = self.env['estate.lease.contract.rental.plan.rel'].search([
                ('contract_id', '=', contract.id),
                ('property_id', 'in', contract.property_ids.ids),
            ])
            return contract.rental_plans_for_property

        return False

    rental_plans_for_property = fields.One2many('estate.lease.contract.rental.plan.rel',
                                                compute='_compute_rental_plans_for_property',
                                                default=lambda self: self._compute_rental_plans_for_property,
                                                string='合同-资产-租金方案', store=False)
    
    """

    """ 这俩函数就是个废柴
    @api.onchange("contract_no")
    def _onchange_contract_no(self):
        print(f"合同管理模型：_onchange_contract_no self.contract_no=【{self.contract_no}】")
        # print(f"合同管理模型：_onchange_contract_no self._id=【{self._id}】")
        print(f"合同管理模型：_onchange_contract_no self._id=【{self.id}】")
        for record in self:

            if record._id:
                self._context = dict(self.env.context, default_contract_id=record._id, default_contract_exist=True)
            else:
                self._context = dict(self.env.context, default_contract_id=None, default_contract_exist=False)

    @api.model
    def default_get(self, fields_list):
        print(f"合同管理模型：default_get self._id=【{self._id}】")
        res = super(EstateLeaseContract, self).default_get(fields_list)
        for record in self:
            _logger.info(f"合同管理模型：default_get record._id=【{record._id}】")
            if self._context.get('active_id'):
                # 当active_id存在时设置context
                res['context'] = dict(self.env.context, default_contract_id=record._id, default_contract_exist=True)
            else:
                res['context'] = dict(self.env.context, default_contract_id=None, default_contract_exist=False)
        return res
    """

    def _set_context(self):
        # 把contract_read_only和session_contract_id写进session
        request.session["contract_read_only"] = self.env.context.get('contract_read_only')
        request.session["menu_root"] = self.env.context.get('menu_root')
        _logger.info(f"合同管理模型：session[menu_root]=【{request.session.get('menu_root')}】")
        _logger.info(f"合同管理模型：session[contract_read_only]=【{request.session.get('contract_read_only')}】")
        # 从tree点击某行传递active_id(貌似默认的tree点击事件并无此context)，所以在后边record中设置session
        if self.env.context.get('active_id'):
            request.session["session_contract_id"] = self.env.context.get('active_id')

        for record in self:
            request.session["session_contract_id"] = record.id
            _logger.info(f"合同管理模型：[session_contract_id]=【{request.session.get('session_contract_id')}】")
            # 这里设置的context，在下一个页面尝试获取
            if record.id:
                self = self.with_context(context_contract_id=record.id, default_contract_exist=True)
            else:
                self = self.with_context(context_contract_id=None, default_contract_exist=False)

            _logger.info(f"合同管理模型： context_contract_id=【{self.env.context.get('context_contract_id')}】")
            record.default_context_contract_id = record.id

    default_context_contract_id = fields.Integer(string="contract id in context", compute="_set_context",
                                                 default=_set_context, store=False)

    @api.depends("date_rent_start", "date_rent_end", "days_free")
    def _calc_days_rent_total(self):
        for record in self:
            if record.date_rent_start and record.date_rent_end:
                if record.date_rent_start > record.date_rent_end:
                    raise exceptions.UserError("计租开始日期不能大于计租结束日期")

                date_s = fields.Date.from_string(record.date_rent_start)
                date_e = fields.Date.from_string(record.date_rent_end)
                delta = date_e - date_s
                if record.days_free:
                    if int(record.days_free) > delta.days:
                        raise exceptions.UserError("免租期天数{0}不能大于租赁天数共{3}天[{1}至{2}]！如果不能打开合同界面，"
                                                   "说明您在合同数据保存之后，优惠方案受到调整。那么"
                                                   "请前往优惠方案页面调整免租期天数".format(record.days_free,
                                                                             record.date_rent_start,
                                                                             record.date_rent_end,
                                                                             delta.days))

                year_delta = (delta.days + 1) / 365
                record.days_rent_total = "{0}年（{1}天）".format(round(year_delta, 2), delta.days + 1)
            else:
                record.days_rent_total = ""

    date_deliver = fields.Date("计划交付日期")
    deliver_condition = fields.Char("交付前提条件")
    date_decorate_start = fields.Date("计划装修开始日期")
    date_decorate_end = fields.Date("计划装修结束日期")
    days_decorate = fields.Integer("计划装修天数", default=0, compute="_calc_days_decorate")

    @api.depends("date_decorate_start", "date_decorate_end")
    def _calc_days_decorate(self):
        for record in self:
            if record.date_decorate_start and record.date_decorate_end:
                date_s = fields.Date.from_string(record.date_decorate_start)
                date_e = fields.Date.from_string(record.date_decorate_end)
                delta = date_e - date_s
                record.days_decorate = delta.days + 1
            else:
                record.days_decorate = 0

    contract_type_id = fields.Selection(string="合同类型",
                                        selection=[('lease', '租赁合同'), ('property_management', '物业合同'),
                                                   ('lease_property_management', '租赁及物业合同')], )

    tag_ids = fields.Many2many("estate.lease.contract.tag", string='合同标签', copy=False)

    rent_account = fields.Many2one("estate.lease.contract.bank.account", string='租金收缴账户')

    opening_date = fields.Date(string="计划开业日期")

    rental_plan_ids = fields.One2many("estate.lease.contract.rental.plan", compute='_compute_rental_plan_ids',
                                      string='租金方案', copy=True, tracking=True)

    @api.depends('property_ids')
    def _compute_rental_plan_ids(self):
        for record in self:
            # 获取所有关联的property的rent_plan_id，并去重
            rent_plans = self.env['estate.property'].search([('id', 'in', record.property_ids.ids)]).mapped(
                'rent_plan_id')
            record.rental_plan_ids = rent_plans

    property_management_fee_plan_ids = fields.One2many("estate.lease.contract.property.management.fee.plan",
                                                       compute='_compute_property_management_fee_plan_ids',
                                                       string="物业费方案", copy=True, tracking=True)

    @api.depends('property_ids')
    def _compute_property_management_fee_plan_ids(self):
        for record in self:
            management_fee_plans = self.env['estate.property'].search([('id', 'in', record.property_ids.ids)]).mapped(
                'management_fee_plan_id')
            record.property_management_fee_plan_ids = management_fee_plans

    property_management_fee_account = fields.Many2one("estate.lease.contract.bank.account", string='物业费收缴账户名')

    electricity_account = fields.Many2one("estate.lease.contract.bank.account", string='电费收缴账户名')

    water_bill_account = fields.Many2one("estate.lease.contract.bank.account", string='水费收缴账户名')

    parking_fee_account = fields.Many2one("estate.lease.contract.bank.account", string='停车费收缴账户名')
    pledge_account = fields.Many2one("estate.lease.contract.bank.account", string='押金收缴账户名')

    parking_space_ids = fields.Many2many('parking.space', 'contract_parking_space_rel', 'contract_id',
                                         'parking_space_id',
                                         string='停车位', copy=True, tracking=True)

    parking_space_count = fields.Integer(default=0, string="分配停车位数量", compute="_calc_parking_space_cnt")

    @api.depends("parking_space_ids")
    def _calc_parking_space_cnt(self):
        for record in self:
            record.parking_space_count = 0
            if record.parking_space_ids:
                record.parking_space_count = len(record.parking_space_ids)

    invoicing_address = fields.Char('发票邮寄地址', translate=True, copy=True)
    invoicing_email = fields.Char('电子发票邮箱', translate=True, copy=True)

    sales_person_id = fields.Many2one('res.users', string='招商员', index=True, default=lambda self: self.env.user)
    opt_person_id = fields.Many2one('res.users', string='录入员', index=True, default=lambda self: self.env.user)

    renter_id = fields.Many2one('res.partner', string='承租人', index=True, copy=True, tracking=True)
    renter_company_id = fields.Many2one('res.partner', string='经营公司', index=True, copy=True, tracking=True)

    property_ids = fields.Many2many('estate.property', 'contract_property_rel', 'contract_id', 'property_id',
                                    string='租赁标的', copy=True, tracking=True)

    rent_count = fields.Integer(default=0, string="租赁标的数量", compute="_calc_rent_total_info", copy=False)
    building_area = fields.Float(default=0.0, string="总建筑面积（㎡）", compute="_calc_rent_total_info", copy=False)
    rent_area = fields.Float(default=0.0, string="总计租面积（㎡）", compute="_calc_rent_total_info", copy=False)

    sequence = fields.Integer(compute='_compute_sorted_sequence', store=True, string='排序')

    @api.depends('property_ids')
    def _compute_sorted_sequence(self):
        for record in self:
            if record.property_ids:
                # 获取所有关联 model_b 记录的 sequence 字段中的最小值
                min_sequence = min(estate_property.sequence for estate_property in record.property_ids)
                record.sequence = min_sequence
            else:
                record.sequence = 0

    # 检查该合同的资产是否在其他合同中，且与其计租期重叠
    def _check_property_in_contract(self, rent_property, self_record):
        property_current_contract = self.env['estate.lease.contract'].search(
            [('property_ids', '=', rent_property.id), ('active', '=', True),
             '|', '&', ('date_rent_start', '>=', self_record.date_rent_start),
             ('date_rent_start', '<=', self_record.date_rent_end),
             '|', '&', ('date_rent_end', '>=', self_record.date_rent_start),
             ('date_rent_end', '<=', self_record.date_rent_end),
             '&', ('date_rent_start', '<=', self_record.date_rent_start),
             ('date_rent_end', '>=', self_record.date_rent_end), ])

        return property_current_contract

    @api.depends("property_ids")
    def _calc_rent_total_info(self):
        for record in self:
            record.rent_count = 0
            record.building_area = 0
            record.rent_area = 0
            if record.property_ids:
                for rent_property in record.property_ids:
                    record.rent_count += 1
                    record.building_area += rent_property.building_area
                    record.rent_area += rent_property.rent_area

    rent_amount = fields.Float(default=0.0, string="总月租金（元/月）", readonly=True)
    rent_amount_year = fields.Float(default=0.0, string="总年租金（元/年）", readonly=True)
    rent_amount_first_period = fields.Float(default=0.0, string="首期租金（元）")
    rent_first_period_from = fields.Date(string="首期租金期间（开始日）")
    rent_first_period_to = fields.Date(string="首期租金期间（结束日）")
    rent_first_payment_date = fields.Date(string="首期租金缴纳日")

    contract_incentives_ids = fields.Many2one('estate.lease.contract.incentives', string='优惠方案', copy=False)
    date_incentives_start = fields.Char(string="优惠政策开始日期", readonly=True, compute="_get_incentives_info")
    date_incentives_end = fields.Char(string="优惠政策结束日期", readonly=True, compute="_get_incentives_info")
    days_free = fields.Integer(string="免租期天数", readonly=True, compute="_get_incentives_info")
    business_discount_days = fields.Char(string="经营优惠（天）", readonly=True, compute="_get_incentives_info")
    business_discount_amount = fields.Char(string="经营优惠（元）", readonly=True, compute="_get_incentives_info")
    decoration_discount_days = fields.Char(string="装修优惠（天）", readonly=True, compute="_get_incentives_info")
    decoration_discount_amount = fields.Char(string="装修优惠（元）", readonly=True, compute="_get_incentives_info")
    support_discount_days = fields.Char(string="扶持优惠（天）", readonly=True, compute="_get_incentives_info")
    support_discount_amount = fields.Char(string="扶持优惠（元）", readonly=True, compute="_get_incentives_info")
    special_discount_days = fields.Char(string="专项优惠（天）", readonly=True, compute="_get_incentives_info")
    special_discount_amount = fields.Char(string="专项优惠（元）", readonly=True, compute="_get_incentives_info")
    incentives_days_total = fields.Char(string="总优惠天数", readonly=True, compute="_get_incentives_info")
    incentives_amount_total = fields.Char(string="总优惠金额（元）", readonly=True, compute="_get_incentives_info")
    contract_incentives_description = fields.Text(string="优惠说明", readonly=True, compute="_get_incentives_info")
    contract_rental_payment_day = fields.Char(string="租金支付周期", readonly=True, compute="_get_payment_day_info")

    @api.depends("rental_plan_ids")
    def _get_payment_day_info(self):
        for record in self:
            if record.property_ids:
                formatted_values = []
                for record_property in record.property_ids:
                    payment_period_str = ""
                    if record_property.rent_plan_id.payment_period:
                        payment_period_str = dict(record_property.rent_plan_id._fields['payment_period'].selection).get(
                            record_property.rent_plan_id.payment_period)

                    formatted_values.append(f"{record_property.name}：{payment_period_str}")
                record.contract_rental_payment_day = '； '.join(formatted_values)
                return record.contract_rental_payment_day

    @api.depends("contract_incentives_ids")
    def _get_incentives_info(self):
        for record in self:
            if record.contract_incentives_ids:
                record.date_incentives_start = record.contract_incentives_ids.date_incentives_start
                record.date_incentives_end = record.contract_incentives_ids.date_incentives_end
                record.days_free = record.contract_incentives_ids.days_free
                record.business_discount_days = record.contract_incentives_ids.business_discount_days
                record.business_discount_amount = record.contract_incentives_ids.business_discount_amount
                record.decoration_discount_days = record.contract_incentives_ids.decoration_discount_days
                record.decoration_discount_amount = record.contract_incentives_ids.decoration_discount_amount
                record.support_discount_days = record.contract_incentives_ids.support_discount_days
                record.support_discount_amount = record.contract_incentives_ids.support_discount_amount
                record.special_discount_days = record.contract_incentives_ids.special_discount_days
                record.special_discount_amount = record.contract_incentives_ids.special_discount_amount
                record.incentives_days_total = record.contract_incentives_ids.incentives_days_total
                record.incentives_amount_total = record.contract_incentives_ids.incentives_amount_total
                record.contract_incentives_description = record.contract_incentives_ids.name_description
            else:
                record.date_incentives_start = ""
                record.date_incentives_end = ""
                record.days_free = ""
                record.business_discount_days = ""
                record.business_discount_amount = ""
                record.decoration_discount_days = ""
                record.decoration_discount_amount = ""
                record.support_discount_days = ""
                record.support_discount_amount = ""
                record.special_discount_days = ""
                record.special_discount_amount = ""
                record.incentives_days_total = ""
                record.incentives_amount_total = ""
                record.contract_incentives_description = ""

    advance_collection_of_coupon_deposit_guarantee = fields.Float(default=0.0, string="预收卡券保证金（元）")
    performance_guarantee = fields.Float(default=0.0, string="履约保证金（元）", tracking=True)
    lease_deposit = fields.Float(default=0.0, string="租赁押金（元）", tracking=True)
    property_management_fee_guarantee = fields.Float(default=0.0, string="物管费保证金（元）", tracking=True)

    decoration_deposit = fields.Float(default=0.0, string="装修押金（元）", tracking=True)
    decoration_management_fee = fields.Float(default=0.0, string="装修管理费（元）", tracking=True)
    decoration_water_fee = fields.Float(default=0.0, string="装修水费（元）", tracking=True)
    decoration_electricity_fee = fields.Float(default=0.0, string="装修电费（元）", tracking=True)
    refuse_collection = fields.Float(default=0.0, string="建筑垃圾清运费（元）", tracking=True)
    garbage_removal_fee = fields.Float(default=0.0, string="垃圾清运费（元）", tracking=True)

    description = fields.Text("详细信息", copy=False, tracking=True)

    attachment_ids = fields.Many2many('ir.attachment', string="附件管理", copy=False, tracking=True)

    rental_details = fields.One2many('estate.lease.contract.property.rental.detail', 'contract_id', store=True,
                                     compute='_compute_rental_details', string="租金明细", readonly=False)

    def _compute_edit_on_hist_page(self):
        """合同管理员希望在合同发布后，在查看界面也可以随时修改"""
        if self.env.user.has_group('estate_lease_contract.estate_lease_contract_group_manager'):
            for record in self:
                record.edit_on_hist_page = True
            return True

        if self.env.context.get('contract_read_only'):
            for record in self:
                record.edit_on_hist_page = False
            return False

        for record in self:
            record.edit_on_hist_page = True
        return True

    edit_on_hist_page = fields.Boolean(string='历史页面可编辑', default=_compute_edit_on_hist_page,
                                       compute=_compute_edit_on_hist_page, store=False)

    @api.depends("property_ids", "rental_plan_ids")
    def _compute_rental_details(self):
        # 把计算结果付回给rental_details
        for record in self:
            rental_details = self.env['estate.lease.contract.property.rental.detail'].search(
                [('contract_id', '=', record.id)])
            record.rental_details = rental_details

    # 合同页面金额汇总标签页的刷新按钮动作
    def action_refresh_all_money(self):
        self._compute_property_rental_detail_ids()
        self._compute_rental_details()

    # 刷新租金方案
    def action_refresh_rental_plan(self):
        self._compute_rental_plan_ids()
        self.action_refresh_all_money()

    # 刷新物业费方案
    def action_refresh_management_fee_plan(self):
        self._compute_property_management_fee_plan_ids()

    # 根据租期和租金方案计算租金明细
    @api.depends("date_rent_start", "date_rent_end", "property_ids", "rental_plan_ids")
    def _compute_property_rental_detail_ids(self):
        for record in self:
            if record.date_rent_start and record.date_rent_end and record.property_ids and record.rental_plan_ids:
                generated_rental_details = _generate_details_from_rent_plan(record)
                # 先删除旧纪录
                print("删除掉estate.lease.contract.property.rental.detail其中的contract_id={0}的记录".format(record.id))
                self.env['estate.lease.contract.property.rental.detail'].search(
                    [('contract_id', '=', record.id)]).write({'active': False})
                # 根据租金方案生成的租金明细，逐条生成model：estate.lease.contract.property.rental.detail
                for rental_detail in generated_rental_details:
                    self.env['estate.lease.contract.property.rental.detail'].create({
                        'contract_id': rental_detail['contract_id'],
                        'property_id': rental_detail['property_id'],
                        'rental_amount': rental_detail['rental_amount'],
                        'rental_amount_zh': rental_detail['rental_amount_zh'],
                        'rental_receivable': rental_detail['rental_amount'],  # 创建按时，应收=租金值
                        'rental_period_no': rental_detail['rental_period_no'],
                        'period_date_from': rental_detail['period_date_from'],
                        'period_date_to': rental_detail['period_date_to'],
                        'date_payment': rental_detail['date_payment'],
                        'description': rental_detail['description'],
                        'active': rental_detail['active'],
                    })

    # 合同新建时默认不生效，需要手动修改
    active = fields.Boolean(default=False, copy=False)
    # 合同状态
    state = fields.Selection(
        string='合同状态', tracking=True,
        selection=[('recording', '录入中未生效'), ('to_be_released', '已发布待生效'), ('released', '已发布已生效'),
                   ('invalid', '过期/失效')], default="recording", copy=False
    )

    # 合同终止状态
    terminated = fields.Boolean(default=False, copy=False)

    def action_release_contract(self):
        for record in self:
            if record.terminated:
                raise UserError(_('该合同已经被终止执行，不能再发布'))

            if record.property_ids:
                current_contract_list = []
                for property_id in record.property_ids:
                    if record.date_rent_start and record.date_rent_end:
                        property_current_contract = self._check_property_in_contract(property_id, record)
                        if property_current_contract:
                            for each_contract in property_current_contract:
                                if each_contract.id != record.id:
                                    current_contract_list.append(
                                        f"房屋：【 {property_id.name}】合同：【{each_contract.name}】"
                                        f"租赁期间：【{each_contract.date_rent_start}~{each_contract.date_rent_end}】")

                if current_contract_list:
                    warn_msg = '；'.join(current_contract_list)
                    raise UserError(_('不能发布本合同，因为房屋在其他租赁合同中租赁期重叠：{0}'.format(warn_msg)))

            else:
                raise UserError(_('发布合同需要至少绑定一个租赁标的'))

            record.active = True
            # 根据合同生效日期判断state
            if record.date_start <= date.today():
                record.state = 'released'
            else:
                record.state = 'to_be_released'

            if record.date_rent_end < date.today():
                record.state = 'invalid'

    # 取消发布合同
    def action_cancel_release_contract(self):
        for record in self:
            record.active = False
            record.state = 'recording'

    @api.constrains('property_ids')
    def _check_update(self):
        for record in self:
            if record.state in ['released', 'released']:
                self.action_release_contract()

    def _insert_contract_property_rental_plan_rel(self, records):
        _logger.info(f"进入 _insert_contract_property_rental_plan_rel 方法")
        if records:
            rgt_rcd = records
        else:
            rgt_rcd = self

        for record in rgt_rcd:
            self.env['estate.lease.contract.rental.plan.rel'].flush_model(['contract_id'])
            self.env['estate.lease.contract.rental.plan.rel'].flush_model(['property_id'])
            self.env['estate.lease.contract.rental.plan.rel'].flush_model(['rental_plan_id'])

            for each_property in record.property_ids:
                self.env.cr.execute("INSERT INTO estate_lease_contract_rental_plan_rel ("
                                    "contract_id, property_id, rental_plan_id ) VALUES (%s, %s, %s)",
                                    [record.id, each_property.id,
                                     each_property.rent_plan_id.id if each_property.rent_plan_id.id else None])

            self.env['estate.lease.contract.rental.plan.rel'].invalidate_model(['contract_id'])
            self.env['estate.lease.contract.rental.plan.rel'].invalidate_model(['property_id'])
            self.env['estate.lease.contract.rental.plan.rel'].invalidate_model(['rental_plan_id'])

    @api.model
    def create(self, vals):
        # 将contract_id,property_id,rental_plan_id 写进 estate.lease.contract.rental.plan.rel 表

        records = super().create(vals)

        self._insert_contract_property_rental_plan_rel(records)

        return records

    @api.model
    def write(self, vals):
        _logger.info(f"write1 vals=：{vals}")
        for record in self:
            _logger.info(f"write1 record=个数：{len(record.rental_details)}-{record.rental_details}")

        res = super().write(vals)
        _logger.info(f"write2 vals=：{vals}")
        for record in self:
            _logger.info(f"write2 record=个数：{len(record.rental_details)}-{record.rental_details}")

        self._delete_contract_property_rental_plan_rel()
        self._insert_contract_property_rental_plan_rel(None)

        return res

    def _delete_contract_property_rental_plan_rel(self):

        for record in self:
            self.env['estate.lease.contract.rental.plan.rel'].flush_model(['contract_id'])
            self.env['estate.lease.contract.rental.plan.rel'].flush_model(['property_id'])
            self.env['estate.lease.contract.rental.plan.rel'].flush_model(['rental_plan_id'])

            self.env.cr.execute("DELETE FROM estate_lease_contract_rental_plan_rel "
                                "WHERE contract_id=%s", [record.id])

            self.env['estate.lease.contract.rental.plan.rel'].invalidate_model(['contract_id'])
            self.env['estate.lease.contract.rental.plan.rel'].invalidate_model(['property_id'])
            self.env['estate.lease.contract.rental.plan.rel'].invalidate_model(['rental_plan_id'])

    @api.model
    def ondelete(self):

        for record in self:
            if record.state != 'recording':
                raise UserError(_(f'本合同目前所处状态：{record.state}，不能删除'))
                return

        self._delete_contract_property_rental_plan_rel()
        return super().unlink()

    # 手动续租
    def action_contract_renewal(self):
        # 续租，延用字段：
        default = {
            "contract_no": f"{self.contract_no}-xz-01",
            "date_rent_start": self.date_rent_end + timedelta(days=1),
            "date_rent_end": self.date_rent_end + timedelta(days=1) + (self.date_rent_end - self.date_rent_start),
        }
        return self.copy(default)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):

        default = dict(default or {})

        new_record = super().copy(default)
        title = "资产租赁合同列表（续租录入）"
        # 设置上下文
        context = {
            'search_default_active': False,
            'contract_read_only': False,
            'menu_root': 'estate.lease.contract'
        }
        # 设置域
        domain = [('id', '=', new_record.id), ('active', '=', False)]

        # 跳转到新记录的表单视图
        return self._action_view_record(new_record.id, title, context, domain)

    def _action_view_record(self, record_id, title, context, domain):
        """ 返回一个 action，用于显示指定 ID 的记录的表单视图 """
        action = {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': 'estate.lease.contract',
            'view_mode': 'form',
            'res_id': record_id,
            'context': context,
            'domain': domain,
            'target': 'current',
        }
        return action
