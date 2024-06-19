# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta, datetime, date
from odoo.tools.translate import _

from dateutil.utils import today

from addons.utils.models.utils import Utils
from odoo import fields, models, api, exceptions
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


def _cal_date_payment(current_s, current_e, rental_plan, date_e):
    """rental_plan.payment_date:[
    ('period_end_month_15_pay_next', '租期结束日的15日前付下期费用'),
   ('period_end_month_20_pay_next', '租期结束日的20日前付下期费用'),
   ('period_end_month_25_pay_next', '租期结束日的25日前付下期费用'),
   ('period_end_month_30_pay_next', '租期结束日的30日前付下期费用'),
    ('period_start_7_pay_pre', '租期开始后的7日内付上期抽成费用'),
   ('period_start_10_pay_pre', '租期开始后的10日内付上期抽成费用'),
   ('period_start_15_pay_pre', '租期开始后的15日内付上期抽成费用'),
   ('period_start_18_pay_pre', '租期开始后的18日内付上期抽成费用'),
   ('period_start_20_pay_pre', '租期开始后的20日内付上期抽成费用'),
   ('period_start_25_pay_pre', '租期开始后的25日内付上期抽成费用'),
   ('period_start_1_pay_this', '租期开始后的1日内付本期费用'),
   ('period_start_5_pay_this', '租期开始后的5日内付本期费用'),
   ('period_start_7_pay_this', '租期开始后的7日内付本期费用'),
   ('period_start_10_pay_this', '租期开始后的10日内付本期费用'),
   ('period_start_15_pay_this', '租期开始后的15日内付本期费用'),
   ('period_start_18_pay_this', '租期开始后的18日内付本期费用'),
   ('period_start_30_pay_this', '租期开始后的30日内付本期费用'),]
    """
    if 'start' in rental_plan.payment_date:
        day_cnt = int(rental_plan.payment_date.split('_')[2])
        date_payment = current_s + timedelta(days=day_cnt)
    elif 'end' in rental_plan.payment_date:
        day_cnt = int(rental_plan.payment_date.split('_')[3])
        date_payment = current_e - timedelta(days=day_cnt)

    if 'next' in rental_plan.payment_date:
        if current_e == date_e:
            date_payment = False

    return date_payment


def _cal_rental_amount(month_cnt, current_s, current_e, property_id, rental_plan):
    """
    租金计算方法：先计算年租金，再计算每月租金或每期租金
    年租金=租金单价×计租面积×365
    月租金=年租金÷12
    两个月租金=月租金×2
    三个月租金=月租金×3
    以此类推
    """
    days_delta = current_e - current_s
    # _logger.info(f"record_self=【{record_self}】")
    rental_amount_year = property_id.rent_area * rental_plan.rent_price * 365
    rental_amount_month = rental_amount_year / 12
    rental_amount = rental_amount_month * month_cnt
    return rental_amount


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
    for property_id in record_self.property_ids:
        if property_id.rent_plan_id:
            rental_plan = property_id.rent_plan_id
        else:
            continue

        month_cnt = 1
        if rental_plan.payment_period == 'month':
            month_cnt = 1
        elif rental_plan.payment_period == 'bimonthly':
            month_cnt = 2
        elif rental_plan.payment_period == 'quarterly':
            month_cnt = 3
        elif rental_plan.payment_period == 'half_year':
            month_cnt = 6
        elif rental_plan.payment_period == 'year':
            month_cnt = 12

        current_s = date_s
        period_no = 1
        while current_s <= date_e:

            # 计算本期结束日
            current_tmp = current_s
            for i in range(month_cnt):
                if current_tmp.day == 1:  # 本月1号至月末
                    current_e = (current_tmp.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                elif current_tmp.day <= 29:  # 本月N号至下月N-1号
                    current_e = (current_tmp.replace(day=28) + timedelta(days=4)).replace(day=current_tmp.day - 1)
                else:  # 30或者31日
                    if current_tmp.month != 1:  # 当前月不是1月，下个月就不是2月，下个月的月末就都可以N-1号
                        current_e = (current_tmp.replace(day=28) + timedelta(days=4)).replace(day=current_tmp.day - 1)
                    else:  # 当前月是1月30、31，下个月就是2月，2月的月末必须是3月1号-1天
                        current_e = (current_tmp.replace(month=3)).replace(day=1) - timedelta(days=1)

                current_tmp = current_e + timedelta(days=1)

            # 循环后，再调整结束日期的日至开始日期的日-1
            if current_s.day == 1:  # 1号开始的期间，按照上述逻辑，最后的current_e就是月末，不用调整
                pass
            elif current_s.day <= 29:  # 开始月的日期为29号以下，那么结束月的日子应该是28号
                current_e.replace(day=current_s.day - 1)
            else:  # 开始日期的日为30或者31日
                if current_e.month != 2:  # 结束日期不是在2月，那么其结束日期可以是N-1
                    current_e.replace(day=current_s.day - 1)
                else:  # 结束日期在2月，那么上边逻辑已经计算好了2月末的最后一天小于30、31
                    pass

            if current_e > date_e:
                current_e = date_e

            # 计算支付日期
            date_payment = _cal_date_payment(current_s, current_e, rental_plan, date_e)
            billing_method_str = dict(rental_plan._fields['billing_method'].selection).get(rental_plan.billing_method)
            payment_date_str = dict(rental_plan._fields['payment_date'].selection).get(rental_plan.payment_date)
            rental_amount = _cal_rental_amount(month_cnt, current_s, current_e, property_id, rental_plan)
            rental_amount_zh = Utils.arabic_to_chinese(rental_amount)

            rental_periods_details.append({
                'contract_id': f"{record_self.id}",
                'property_id': f"{property_id.id}",
                'period_date_from': f"{current_s.strftime('%Y-%m-%d')}",
                'period_date_to': f"{current_e.strftime('%Y-%m-%d')}",
                'date_payment': date_payment,
                'rental_amount': f"{rental_amount}",
                'rental_amount_zh': f"{rental_amount_zh}",
                'rental_period_no': f"{period_no}",
                'description': f"{rental_plan.name}-{billing_method_str}-"
                               f"{payment_date_str}",
            })

            # 下期开始日
            current_s = current_e + timedelta(days=1)
            period_no += 1

        print("{1}.rental_periods={0}".format(rental_periods_details, rental_plan.name))

    return rental_periods_details


class EstateLeaseContract(models.Model):
    _name = "estate.lease.contract"
    _description = "资产租赁合同管理模型"
    _order = "contract_no, id"

    name = fields.Char('合同名称', required=True, translate=True, copy=False, default="")

    contract_no = fields.Char('合同编号', required=True, translate=True, copy=False, default="")
    # contract_amount = fields.Float("合同金额", default=0.0)
    # contract_tax = fields.Float("税额", default=0.0)
    # contract_tax_per = fields.Float("税率", default=0.0)
    # contract_tax_out = fields.Float("不含税合同额", default=0.0)

    date_sign = fields.Date("合同签订日期", required=True, copy=False)
    date_start = fields.Date("合同开始日期", required=True, copy=False)

    date_rent_start = fields.Date("计租开始日期", required=True, copy=False)
    date_rent_end = fields.Date("计租结束日期", required=True, copy=False)

    days_rent_total = fields.Char(string="租赁期限", compute="_calc_days_rent_total")

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
                                      string='租金方案', copy=False)

    @api.depends('property_ids')
    def _compute_rental_plan_ids(self):
        for record in self:
            # 获取所有关联的property的rent_plan_id，并去重
            rent_plans = self.env['estate.property'].search([('id', 'in', record.property_ids.ids)]).mapped(
                'rent_plan_id')
            record.rental_plan_ids = rent_plans

    property_management_fee_plan_ids = fields.One2many("estate.lease.contract.property.management.fee.plan",
                                                       compute='_compute_property_management_fee_plan_ids',
                                                       string="物业费方案", copy=False)

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
                                         string='停车位', copy=False)

    parking_space_count = fields.Integer(default=0, string="分配停车位数量", compute="_calc_parking_space_cnt")

    @api.depends("parking_space_ids")
    def _calc_parking_space_cnt(self):
        for record in self:
            record.parking_space_count = 0
            if record.parking_space_ids:
                record.parking_space_count = len(record.parking_space_ids)

    invoicing_address = fields.Char('发票邮寄地址', translate=True, copy=False)
    invoicing_email = fields.Char('电子发票邮箱', translate=True, copy=False)

    sales_person_id = fields.Many2one('res.users', string='招商员', index=True, default=lambda self: self.env.user)
    opt_person_id = fields.Many2one('res.users', string='录入员', index=True, default=lambda self: self.env.user)

    renter_id = fields.Many2one('res.partner', string='承租人', index=True, copy=False)

    property_ids = fields.Many2many('estate.property', 'contract_property_rel', 'contract_id', 'property_id',
                                    string='租赁标的', copy=False)

    rent_count = fields.Integer(default=0, string="租赁标的数量", compute="_calc_rent_total_info", copy=False)
    building_area = fields.Float(default=0.0, string="总建筑面积（㎡）", compute="_calc_rent_total_info", copy=False)
    rent_area = fields.Float(default=0.0, string="总计租面积（㎡）", compute="_calc_rent_total_info", copy=False)

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

    rent_amount = fields.Float(default=0.0, string="总月租金（元/月）")
    rent_amount_first_period = fields.Float(default=0.0, string="首期租金（元）")
    rent_first_period_from = fields.Date(string="首期租金期间（开始日）")
    rent_first_period_to = fields.Date(string="首期租金期间（结束日）")
    rent_first_payment_date = fields.Date(string="首期租金缴纳日")

    contract_incentives_ids = fields.Many2one('estate.lease.contract.incentives', string='优惠方案', copy=False)
    date_incentives_start = fields.Char(string="优惠政策开始日期", readonly=True, compute="_get_incentives_info")
    date_incentives_end = fields.Char(string="优惠政策结束日期", readonly=True, compute="_get_incentives_info")
    days_free = fields.Char(string="免租期天数", readonly=True, compute="_get_incentives_info")
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
    performance_guarantee = fields.Float(default=0.0, string="履约保证金（元）")
    property_management_fee_guarantee = fields.Float(default=0.0, string="物管费保证金（元）")

    decoration_deposit = fields.Float(default=0.0, string="装修押金（元）")
    decoration_management_fee = fields.Float(default=0.0, string="装修管理费（元）")
    decoration_water_fee = fields.Float(default=0.0, string="装修水费（元）")
    decoration_electricity_fee = fields.Float(default=0.0, string="装修电费（元）")
    refuse_collection = fields.Float(default=0.0, string="建筑垃圾清运费（元）")
    garbage_removal_fee = fields.Float(default=0.0, string="垃圾清运费（元）")

    description = fields.Text("详细信息", copy=False)

    attachment_ids = fields.Many2many('ir.attachment', string="附件管理", copy=False)

    rental_details = fields.One2many('estate.lease.contract.property.rental.detail', 'contract_id',
                                     compute='_compute_rental_details', string="租金明细")

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
                    [('contract_id', '=', record.id)]).unlink()
                # 根据租金方案生成的租金明细，逐条生成model：estate.lease.contract.property.rental.detail
                for rental_detail in generated_rental_details:
                    self.env['estate.lease.contract.property.rental.detail'].create({
                        'contract_id': rental_detail['contract_id'],
                        'property_id': rental_detail['property_id'],
                        'rental_amount': rental_detail['rental_amount'],
                        'rental_amount_zh': rental_detail['rental_amount_zh'],
                        'rental_period_no': rental_detail['rental_period_no'],
                        'period_date_from': rental_detail['period_date_from'],
                        'period_date_to': rental_detail['period_date_to'],
                        'date_payment': rental_detail['date_payment'],
                        'description': rental_detail['description'],
                    })

    # 合同新建时默认不生效，需要手动修改
    active = fields.Boolean(default=False, copy=False)
    # 合同状态
    state = fields.Selection(
        string='合同状态',
        selection=[('recording', '录入中未生效'), ('to_be_released', '已发布待生效'), ('released', '已发布已生效'),
                   ('invalid', '失效')], default="recording", copy=False
    )

    # 合同终止状态
    terminated = fields.Boolean(default=False, copy=False)

    # 发布合同
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
