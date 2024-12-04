# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import logging
import zipfile
from datetime import timedelta, datetime, date
import random
from io import BytesIO
from typing import Dict, List

from odoo.http import request
from odoo.tools.safe_eval import time
from odoo.tools.translate import _

from dateutil.utils import today

from addons.utils.models.utils import Utils
from odoo import fields, models, api, exceptions
from odoo.exceptions import UserError, ValidationError, AccessError
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

    return rental_amount


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
                                   'rent_amount_adapt': base_rent_amount_monthly_val * (
                                           1 + (period_percentage.billing_progress_info_up_percentage / 100)),
                                   'rent_price_adapt': base_rent_price * (
                                           1 + (period_percentage.billing_progress_info_up_percentage / 100)),
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

    if date_e and current_e > date_e:
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
    temp_rent_amount_year = 0.0
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
            rent_amount_monthly_val = rental_plan.rent_price * property_id.rent_area * 365 / 12
        # ↑↑↑不能在这里四舍五入

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
            rental_amount_zh = Utils.arabic_to_chinese(round(rental_amount, 2))

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
                'active': True,
                'edited': False,
            })

            # 下期开始日
            current_s = current_e + timedelta(days=1)
            period_no += 1

        temp_rent_amount += rent_amount_monthly_val  # 这里还是显示基础月租
        # 手调年租金仅显示
        if property_id.rent_amount_yearly_adjust_4_view:
            _logger.info(f"property_id.rent_amount_yearly_adjust={property_id.rent_amount_yearly_adjust}")
            temp_rent_amount_year += property_id.rent_amount_yearly_adjust
        else:
            temp_rent_amount_year += rent_amount_monthly_val * 12

        _logger.info(f"{rental_plan.name}.rental_periods={rental_periods_details}")
        _logger.info(f"temp_rent_amount={temp_rent_amount}")
        _logger.info(f"temp_rent_amount_year={temp_rent_amount_year}")

    record_self.rent_amount = temp_rent_amount
    record_self.rent_amount_year = temp_rent_amount_year
    record_self.lease_deposit = temp_deposit_amount

    return rental_periods_details


class Partner(models.Model):
    _description = '直接输入名称创建partner'
    _inherit = 'res.partner'

    contract_party_b_id = fields.One2many(comodel_name="estate.lease.contract", inverse_name="renter_id",
                                          string="乙方单位/个人", copy=False)
    contract_party_b_contact_name = fields.Char(string="联系人", compute="_compute_party_b_contact_info")
    contract_party_b_contact_tel = fields.Char(string="联系方式", compute="_compute_party_b_contact_info")
    party_b_properties = fields.Text(string="租赁信息", compute="_compute_party_b_properties")
    contracts_valid = fields.Boolean(string="合同有效", compute="_compute_contracts_valid", store=True)
    registered_capital = fields.Float(string="注册资金（万元）")

    @api.depends("contract_party_b_id", "contract_party_b_contact_name", "party_b_properties")
    def _compute_contracts_valid(self):
        for record in self:
            for contract in record.contract_party_b_id:
                if not contract.terminated and contract.date_rent_end >= fields.Date.today():
                    record.contracts_valid = True
                    break
            record.contracts_valid = False

    def _compute_party_b_properties(self):
        for record in self:
            property_info = []
            for contract in record.contract_party_b_id:
                for property_id in contract.property_ids:
                    property_info.append((property_id.name,
                                          contract.date_rent_start.strftime('%Y-%m-%d') + '-' +
                                          contract.date_rent_end.strftime('%Y-%m-%d')))
            if property_info:
                record.party_b_properties = str(sorted(property_info,
                                                       key=lambda property_i: property_i[1],
                                                       reverse=True)).lstrip('[').rstrip(']')
            else:
                record.party_b_properties = False

    def _compute_party_b_contact_info(self):
        for record in self:
            contact = record.child_ids.filtered(lambda r: not r.is_company)
            if contact:
                record.contract_party_b_contact_name = contact[0].name
                record.contract_party_b_contact_tel = contact[0].phone if contact[0].phone else contact[0].mobile
            else:
                record.contract_party_b_contact_name = record.name
                record.contract_party_b_contact_tel = record.phone if record.phone else record.mobile

    @api.model
    def name_create(self, name):
        """复写此方法为了能把company_id写库"""

        partner_id, display_name = super().name_create(name)
        _logger.debug(f"self.env.user.company_id={self.env.user.company_id}")
        self.env['res.partner'].search([('id', '=', partner_id)]).write({'company_id': self.env.user.company_id.id})

        return partner_id, display_name

    def automatic_set_party_a_status(self):
        # 更新本公司下的花名册
        _logger.debug(f"self.env.user.company_id={self.env.user.company_id}")
        partners = self.env['res.partner'].search([('company_id', '=', self.env.user.company_id.id)])
        _logger.info(f"准备更新partners={partners}")
        need_commit = False
        set_2_true = []
        set_2_false = []
        for partner in partners:
            _logger.debug(f"partner={partner}；partner.contract_party_b_id={partner.contract_party_b_id}")
            partner_contract_valid_cnt = 0
            for contract in partner.contract_party_b_id:
                _logger.debug(f"contract={contract};terminated={contract.terminated};"
                              f"date_rent_end={contract.date_rent_end};today={fields.Date.today()}")
                if not contract.terminated and contract.date_rent_end >= fields.Date.today():
                    partner_contract_valid_cnt += 1
                    if not partner.contracts_valid:
                        _logger.debug(f"partner.contracts_valid={partner.contracts_valid}改为True")
                        set_2_true.append(partner.id)
                    break
            if partner_contract_valid_cnt == 0 and partner.contracts_valid:
                _logger.debug(f"partner.contracts_valid={partner.contracts_valid}改为False")
                set_2_false.append(partner.id)

        if set_2_true:
            _logger.debug(f"更新为true：{set_2_true}")
            if len(set_2_true) == 1:
                self.env.cr.execute(f"UPDATE res_partner SET contracts_valid = true WHERE id = {set_2_true[0]}")
            else:
                self.env.cr.execute(f"UPDATE res_partner SET contracts_valid = true WHERE id in {tuple(set_2_true)}")
            need_commit = True

        if set_2_false:
            _logger.debug(f"更新为false：{set_2_false}")
            if len(set_2_false) == 1:
                self.env.cr.execute(f"UPDATE res_partner SET contracts_valid = false WHERE id = {set_2_false[0]}")
            else:
                self.env.cr.execute(f"UPDATE res_partner SET contracts_valid = false WHERE id in {tuple(set_2_false)}")
            need_commit = True

        if need_commit:
            self.env.cr.commit()

        action = {
            "name": "入驻企业花名册",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "estate.lease.contract",
            "views": [
                (self.env.ref('estate_lease_contract.estate_lease_contract_party_b_view_tree').id, 'tree'),
                (False, 'form')],
            "context": {
                'search_default_state_valid': True,
                'menu_root': 'estate.lease.contract',
                'from_menu_click_tree': True,
            },
            "domain": [('company_id', 'in', self.env.user.company_ids.ids)],
        }
        return action


class EstateLeaseContract(models.Model):
    # def onchange(self, values, field_names, fields_spec):
    #     super().onchange(values, field_names, fields_spec)

    _name = "estate.lease.contract"
    _description = "资产租赁合同管理模型"
    _order = "sequence ASC, renter_id ASC, date_rent_end DESC"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    name = fields.Char('合同名称', required=True, translate=True, copy=True,
                       default=lambda self: self._get_default_name())
    party_a_unit_id = fields.Many2one(comodel_name="estate.lease.contract.party.a.unit", string="甲方",
                                      default=lambda self: self._get_party_a_unit_id())
    party_a_unit_invisible = fields.Boolean(default=lambda self: self._get_party_a_unit_invisible(),
                                            compute="_get_party_a_unit_invisible")
    contract_no = fields.Char('合同编号', required=True, translate=True, copy=False,
                              default=lambda self: self._get_contract_no(False))
    # contract_amount = fields.Float("合同金额", default=0.0)
    # contract_tax = fields.Float("税额", default=0.0)
    # contract_tax_per = fields.Float("税率", default=0.0)
    # contract_tax_out = fields.Float("不含税合同额", default=0.0)

    date_sign = fields.Date("合同签订日期", required=True, copy=False, default=fields.Date.context_today, tracking=True)
    property_state_by_date_sign = fields.Boolean(string="资产出租状态依据", default=False)
    date_start = fields.Date("合同开始日期", required=True, copy=False, default=fields.Date.context_today, tracking=True)
    property_state_by_date_start = fields.Boolean(string="资产出租状态依据", default=True)
    date_rent_start = fields.Date("计租开始日期", required=True, copy=False, tracking=True,
                                  default=fields.Date.context_today)
    property_state_by_date_rent_start = fields.Boolean(string="资产出租状态依据", default=False)
    date_rent_end = fields.Date("计租结束日期", required=True, copy=False, tracking=True,
                                default=lambda self: self._get_default_date_rent_end())

    days_rent_total = fields.Char(string="租赁期限", compute="_calc_days_rent_total")

    # 相当于合同历史信息：资产名称、计租面积、押金月数、押金金额，其他信息还是从资产和租赁方案中取（资产和租赁方案修改保存时，做覆盖和影响的提示）
    # *********在查看界面（也就是说只要合同发布），那么就应该显示历史数据，录入中的则显示关联master property和rental plan的信息*********
    contract_hist = fields.One2many('estate.lease.contract.rental.plan.rel', 'contract_id',
                                    string='合同-资产-租金方案历史信息', copy=False)

    @api.onchange("date_sign")
    def _onchange_date_sign(self):
        if self.date_sign > self.date_start:
            self.date_start = self.date_sign

    @api.onchange("date_start")
    def _onchange_date_start(self):
        if self.date_start < self.date_sign:
            self.date_sign = self.date_start
        if self.date_start > self.date_rent_start:
            self.date_rent_start = self.date_start

    @api.onchange("date_rent_start")
    def _onchange_date_rent_start(self):
        if self.date_rent_start < self.date_start:
            self.date_start = self.date_rent_start
        if self.date_rent_start > self.date_rent_end:
            self.date_rent_end = self.date_rent_start

    @api.onchange("date_rent_end")
    def _onchange_date_rent_end(self):
        if self.date_rent_end < self.date_rent_start:
            self.date_rent_start = self.date_rent_end

    @api.onchange("property_state_by_date_sign")
    def _onchange_property_state_by_date_sign(self):
        if self.property_state_by_date_sign:
            if self.property_state_by_date_start:
                self.property_state_by_date_start = False
            if self.property_state_by_date_rent_start:
                self.property_state_by_date_rent_start = False
        else:
            if self.property_state_by_date_start and self.property_state_by_date_rent_start:
                self.property_state_by_date_rent_start = False
            if (not self.property_state_by_date_start) and (not self.property_state_by_date_rent_start):
                self.property_state_by_date_start = True

    @api.onchange("property_state_by_date_start")
    def _onchange_property_state_by_date_start(self):
        if self.property_state_by_date_start:
            if self.property_state_by_date_sign:
                self.property_state_by_date_sign = False
            if self.property_state_by_date_rent_start:
                self.property_state_by_date_rent_start = False
        else:
            if self.property_state_by_date_rent_start and self.property_state_by_date_sign:
                self.property_state_by_date_sign = False
            if (not self.property_state_by_date_rent_start) and (not self.property_state_by_date_sign):
                self.property_state_by_date_rent_start = True

    @api.onchange("property_state_by_date_rent_start")
    def _onchange_property_state_by_date_rent_start(self):
        if self.property_state_by_date_rent_start:
            if self.property_state_by_date_sign:
                self.property_state_by_date_sign = False
            if self.property_state_by_date_start:
                self.property_state_by_date_start = False
        else:
            if self.property_state_by_date_sign and self.property_state_by_date_start:
                self.property_state_by_date_sign = False
            if (not self.property_state_by_date_start) and (not self.property_state_by_date_sign):
                self.property_state_by_date_start = True

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

    def _get_party_a_unit_id(self):
        return self.env['estate.lease.contract.party.a.unit'].search([('company_id', '=',
                                                                       self.env.user.company_id.id)], limit=1)

    def _get_party_a_unit_invisible(self):
        result = self.env['estate.lease.contract.party.a.unit'].search([('company_id', '=',
                                                                         self.env.user.company_id.id)])

        if result and len(result) > 1:
            res = False
        else:
            res = True

        for record in self:
            record.party_a_unit_invisible = res

        return res

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
                    raise exceptions.UserError("计租结束日期不能小于计租开始日期")

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

    contract_type_id = fields.Selection(string="合同类型", default="lease",
                                        selection=[('lease', '租赁合同'), ('property_management', '物业合同'),
                                                   ('lease_property_management', '租赁及物业合同')], )

    tag_ids = fields.Many2many("estate.lease.contract.tag", string='合同标签', copy=False)

    rent_account = fields.Many2one("estate.lease.contract.bank.account", string='租金收缴账户')
    rent_account_bank_name = fields.Char("租金户银行名称", related="rent_account.bank_name")
    rent_account_bank_branch_name = fields.Char("租金户分行名称", related="rent_account.bank_branch_name")
    rent_account_bank_account_name = fields.Char("租金户银行账户名", related="rent_account.bank_account_name")
    rent_account_bank_account_id = fields.Char("租金户银行账号", related="rent_account.bank_account_id")

    opening_date = fields.Date(string="计划开业日期")

    rental_plan_ids = fields.One2many("estate.lease.contract.rental.plan", compute='_compute_rental_plan_ids',
                                      string='租金方案', copy=True, tracking=True)

    @api.depends('property_ids')
    def _compute_rental_plan_ids(self):
        for record in self:
            _logger.debug(f"_compute_rental_plan_ids called record.id={record.id}")
            # 获取所有关联的property的rent_plan_id，并去重
            rent_plans = self.env['estate.property'].search([('id', 'in', record.property_ids.ids)]).mapped(
                'rent_plan_id')
            record.rental_plan_ids = rent_plans

            # 排除页面上做了删除动作的租赁标的
            _logger.debug(f"record.property_ids.ids={record.property_ids.ids}")
            for rent_plan in record.rental_plan_ids:
                _logger.debug(f"开始清理{rent_plan.name}其中rent_plan.rent_targets={rent_plan.rent_targets.ids}")
                tgt_keep = []
                for rent_tgt in rent_plan.rent_targets:
                    _logger.debug(f"rent_tgt.id={rent_tgt.id}")
                    tgt_id = rent_tgt._origin.id if isinstance(rent_tgt.id, models.NewId) else rent_tgt.id
                    if tgt_id in record.property_ids.ids:
                        tgt_keep.append(tgt_id)
                _logger.debug(f"tgt_keep={tgt_keep}")
                rent_plan.rent_targets = tgt_keep

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
    property_management_fee_account_bank_name = fields.Char(
        "物业费账户银行名称", related="property_management_fee_account.bank_name")
    property_management_fee_account_bank_branch_name = fields.Char(
        "物业费账户分行名称", related="property_management_fee_account.bank_branch_name")
    property_management_fee_account_bank_account_name = fields.Char(
        "物业费账户银行账户名", related="property_management_fee_account.bank_account_name")
    property_management_fee_account_bank_account_id = fields.Char(
        "物业费账户银行账号", related="property_management_fee_account.bank_account_id")

    electricity_account = fields.Many2one("estate.lease.contract.bank.account", string='电费收缴账户名')
    electricity_account_bank_name = fields.Char("电费账户银行名称", related="electricity_account.bank_name")
    electricity_account_bank_branch_name = fields.Char("电费账户分行名称", related="electricity_account.bank_branch_name")
    electricity_account_bank_account_name = fields.Char("电费账户银行账户名",
                                                        related="electricity_account.bank_account_name")
    electricity_account_bank_account_id = fields.Char("电费账户银行账号", related="electricity_account.bank_account_id")

    water_bill_account = fields.Many2one("estate.lease.contract.bank.account", string='水费收缴账户名')
    water_bill_account_bank_name = fields.Char("水费账户银行名称", related="water_bill_account.bank_name")
    water_bill_account_bank_branch_name = fields.Char("水费账户分行名称", related="water_bill_account.bank_branch_name")
    water_bill_account_bank_account_name = fields.Char("水费账户银行账户名", related="water_bill_account.bank_account_name")
    water_bill_account_bank_account_id = fields.Char("水费账户银行账号", related="water_bill_account.bank_account_id")

    heat_bill_account = fields.Many2one("estate.lease.contract.bank.account", string='取暖费收缴账户名')
    heat_bill_account_bank_name = fields.Char("取暖费账户银行名称", related="heat_bill_account.bank_name")
    heat_bill_account_bank_branch_name = fields.Char("取暖费账户分行名称", related="heat_bill_account.bank_branch_name")
    heat_bill_account_bank_account_name = fields.Char("取暖费账户银行账户名", related="heat_bill_account.bank_account_name")
    heat_bill_account_bank_account_id = fields.Char("取暖费账户银行账号", related="heat_bill_account.bank_account_id")

    parking_fee_account = fields.Many2one("estate.lease.contract.bank.account", string='停车费收缴账户名')
    parking_fee_account_bank_name = fields.Char("停车费账户银行名称", related="parking_fee_account.bank_name")
    parking_fee_account_bank_branch_name = fields.Char("停车费账户分行名称", related="parking_fee_account.bank_branch_name")
    parking_fee_account_bank_account_name = fields.Char("停车费账户银行账户名", related="parking_fee_account.bank_account_name")
    parking_fee_account_bank_account_id = fields.Char("停车费账户银行账号", related="parking_fee_account.bank_account_id")

    pledge_account = fields.Many2one("estate.lease.contract.bank.account", string='押金收缴账户名')
    pledge_account_bank_name = fields.Char("押金户银行名称", related="pledge_account.bank_name")
    pledge_account_bank_branch_name = fields.Char("押金户分行名称", related="pledge_account.bank_branch_name")
    pledge_account_bank_account_name = fields.Char("押金户银行账户名", related="pledge_account.bank_account_name")
    pledge_account_bank_account_id = fields.Char("押金户银行账号", related="pledge_account.bank_account_id")

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

    sales_person_id = fields.Many2one('res.users', string='招商员（中介）', index=True, default=lambda self: self.env.user,
                                      domain="[('company_id', '=', company_id)]")
    opt_person_id = fields.Many2one('res.users', string='录入员', index=True, default=lambda self: self.env.user,
                                    domain="[('company_id', '=', company_id)]")

    renter_id = fields.Many2one('res.partner', string='承租人', index=True, copy=True, tracking=True,
                                domain="[('company_id', '=', company_id)]")
    renter_company_id = fields.Many2one('res.partner', string='在地经营公司', index=True, copy=True, tracking=True,
                                        domain="[('company_id', '=', company_id)]")
    renter_contact_name = fields.Char(string="承租方负责人", compute="_compute_renter_contact_info")
    renter_contact_tel = fields.Char(string="联系方式", compute="_compute_renter_contact_info")
    property_ids = fields.Many2many('estate.property', 'contract_property_rel', 'contract_id', 'property_id',
                                    string='租赁标的', copy=True, tracking=True,
                                    domain="[('company_id', '=', company_id)]")

    rent_count = fields.Integer(default=0, string="租赁标的数量", compute="_calc_rent_total_info", copy=False)
    building_area = fields.Float(default=0.0, string="总建筑面积（㎡）", compute="_calc_rent_total_info", copy=False)
    rent_area = fields.Float(default=0.0, string="总计租面积（㎡）", compute="_calc_rent_total_info", copy=False)
    brokerage_fee = fields.Float(default=0.0, string="中介费（元）", copy=False)
    comments = fields.Html(string='合同备注')
    sequence = fields.Integer(compute='_compute_sorted_sequence', store=True, string='可在列表页面拖拽排序')
    order_by_name = fields.Boolean(string="以名称排序", default=True,
                                   help="勾选则以租赁标的名称为排序基准，不勾选则以合同列表中的拖拽顺序为排序基准")
    vat = fields.Char("企业统一信用代码", related="renter_id.vat")
    registered_capital = fields.Float(string="注册资金（万元）", related="renter_id.registered_capital")
    industry_id = fields.Many2one('res.partner.industry', string='行业类型', related="renter_id.industry_id")

    @api.depends('renter_id')
    def _compute_renter_contact_info(self):
        for record in self:
            # 查找partner的child_ids中is_company=False的记录，这通常代表个人联系人
            contact = record.renter_id.child_ids.filtered(lambda r: not r.is_company)
            if contact:
                for each_c in contact:
                    check_str = str(each_c.name) + str(each_c.title.name) + str(each_c.function) + str(each_c.comment)
                    _logger.info(f"承租方负责人check_str=[{check_str}]")
                    if '责' in check_str:
                        record.renter_contact_name = each_c.name
                        record.renter_contact_tel = each_c.phone if each_c.phone else each_c.mobile
                        break

                if not record.renter_contact_name:
                    record.renter_contact_name = contact[0].name
                    record.renter_contact_tel = contact[0].phone if contact[0].phone else contact[0].mobile

            else:
                record.renter_contact_name = record.renter_id.name
                record.renter_contact_tel = record.renter_id.phone \
                    if record.renter_id.phone else record.renter_id.mobile

    @api.depends('property_ids', 'name', 'order_by_name')
    def _compute_sorted_sequence(self):
        for record in self:
            record.sequence = record.sequence
            if record.order_by_name:
                if record.property_ids:
                    # 获取所有关联 model_b 记录的 sequence 字段中的最小值
                    min_sequence = min(estate_property.sequence for estate_property in record.property_ids)
                    if record.sequence != min_sequence:
                        record.sequence = min_sequence
                else:
                    record.sequence = 0

            all_rcds = self.env['estate.lease.contract'].search([('company_id', '=', self.company_id.id),
                                                                 ('active', 'in', [True, False])])
            _logger.info(f"排序self.company_id.id={self.company_id.id}contract集合all_rcds={all_rcds}")
            for rcd in all_rcds:
                if rcd.order_by_name and rcd.property_ids:
                    min_sequence = min(each_property.sequence for each_property in rcd.property_ids)
                    if rcd.sequence != min_sequence:
                        _logger.info(f"重新排序contract rcd{rcd.id}.sequence={rcd.sequence}→{min_sequence}")
                        rcd.sequence = min_sequence

    # 检查该合同的资产是否在其他合同中，且与其计租期重叠
    def _check_property_in_contract(self, rent_property, self_record):
        property_current_contract = self.env['estate.lease.contract'].search(
            [('property_ids', '=', rent_property.id), ('active', '=', True), ('terminated', '=', False),
             ('state', 'in', ['released', 'to_be_released']),
             '|', '&', ('date_rent_start', '>=', self_record.date_rent_start),
             ('date_rent_start', '<=', self_record.date_rent_end),
             '|', '&', ('date_rent_end', '>=', self_record.date_rent_start),
             ('date_rent_end', '<=', self_record.date_rent_end),
             '&', ('date_rent_start', '<=', self_record.date_rent_start),
             ('date_rent_end', '>=', self_record.date_rent_end), ])

        return property_current_contract

    # 检查该合同中分配的注册地址是否在其他合同中
    def _check_registration_addr_in_contract(self, registration_addr_id, self_record):
        property_current_contract = self.env['estate.lease.contract'].search(
            [('registration_addr', '=', registration_addr_id), ('active', '=', True), ('terminated', '=', False),
             ('state', 'in', ['released', 'to_be_released']),
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
            rent_cnt_total = 0
            building_area_total = 0
            rent_area_total = 0
            rent_amount_total = 0
            rent_amount_year_total = 0
            deposit_total = 0
            deposit_receivable_total = 0
            deposit_received_total = 0
            deposit_arrears_total = 0
            if record.property_ids:
                if record.state == "recording":
                    for rent_property in record.property_ids:
                        rent_cnt_total += 1
                        building_area_total += rent_property.building_area
                        rent_area_total += rent_property.rent_area
                        rent_amount_total += rent_property.rent_amount_monthly_adjust if \
                            rent_property.rent_amount_monthly_adjust else rent_property.rent_amount_monthly_auto
                        # 不管是recording 还是非recording，都要看这个property的手调年租金是不是仅显示用
                        if not rent_property.rent_amount_yearly_adjust_4_view:
                            rent_amount_year_total += 12 * rent_property.rent_amount_monthly_adjust if \
                                rent_property.rent_amount_monthly_adjust else rent_property.rent_amount_monthly_auto
                        else:
                            rent_amount_year_total += rent_property.rent_amount_yearly_adjust

                        deposit_total += rent_property.deposit_amount
                        deposit_receivable_total += rent_property.deposit_amount
                        deposit_received_total += 0
                        deposit_arrears_total += deposit_receivable_total
                else:
                    for each_hist in record.contract_hist:
                        rent_cnt_total += 1
                        building_area_total += each_hist.contract_property_building_area
                        rent_area_total += each_hist.contract_property_area
                        rent_amount_total += each_hist.contract_rent_amount_monthly
                        rent_amount_year_total += each_hist.contract_rent_amount_year
                        deposit_total += each_hist.contract_deposit_amount
                        deposit_receivable_total += each_hist.contract_deposit_amount
                        deposit_received_total += each_hist.contract_deposit_amount_received
                        deposit_arrears_total += each_hist.contract_deposit_amount_arrears

            record.rent_count = rent_cnt_total
            record.building_area = building_area_total
            record.rent_area = rent_area_total
            record.rent_amount = rent_amount_total
            record.rent_amount_year = rent_amount_year_total
            record.lease_deposit = deposit_total
            record.lease_deposit_receivable = deposit_receivable_total
            record.lease_deposit_received = deposit_received_total
            record.lease_deposit_arrears = deposit_arrears_total

    rent_amount = fields.Float(default=0.0, string="总月租金（元/月）", compute="_calc_rent_total_info", readonly=True)
    rent_amount_year = fields.Float(default=0.0, string="总年租金（元/年）", compute="_calc_rent_total_info", readonly=True)
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
    lease_deposit = fields.Float(default=0.0, string="租赁押金（元）", compute="_calc_rent_total_info", tracking=True,
                                 copy=False)
    lease_deposit_receivable = fields.Float(default=0.0, string="押金应收（元）", compute="_calc_rent_total_info",
                                            tracking=True, copy=False)
    lease_deposit_received = fields.Float(default=0.0, string="押金实收（元）", compute="_calc_rent_total_info",
                                          tracking=True, copy=False)
    lease_deposit_arrears = fields.Float(default=0.0, string="押金欠缴（元）", compute="_calc_rent_total_info",
                                         tracking=True, copy=False)
    property_management_fee_guarantee = fields.Float(default=0.0, string="物管费保证金（元）", tracking=True)

    decoration_deposit = fields.Float(default=0.0, string="装修押金（元）", tracking=True, copy=False)
    decoration_management_fee = fields.Float(default=0.0, string="装修管理费（元）", tracking=True, copy=False)
    decoration_water_fee = fields.Float(default=0.0, string="装修水费（元）", tracking=True, copy=False)
    decoration_electricity_fee = fields.Float(default=0.0, string="装修电费（元）", tracking=True, copy=False)
    refuse_collection = fields.Float(default=0.0, string="建筑垃圾清运费（元）", tracking=True, copy=False)
    garbage_removal_fee = fields.Float(default=0.0, string="垃圾清运费（元）", tracking=True, copy=False)

    description = fields.Text("详细信息", copy=False, tracking=True)
    registration_addr = fields.Many2many(string="注册地址", comodel_name="estate.registration.addr",
                                         copy=False, tracking=True)
    registration_addr_count = fields.Integer(string="注册地址数量（个）", copy=False,
                                             compute="_compute_registration_addr_count")
    registration_addr_sum = fields.Integer(string="注册地址金额（元）", copy=False,
                                           compute="_compute_registration_addr_count")
    contract_registration_addr_rel_id = fields.One2many(string="合同分配的注册地址", copy=False,
                                                        comodel_name="estate.lease.contract.registration.addr.rel",
                                                        inverse_name="contract_id")
    contract_registration_addr_rel_archived = fields.One2many(string="合同分配的注册地址(已归档)",
                                                              comodel_name="estate.lease.contract.registration.addr.rel",
                                                              inverse_name="contract_id")
    attachment_ids = fields.Many2many('ir.attachment', string="附件管理", copy=False, tracking=True)

    rental_details = fields.One2many('estate.lease.contract.property.rental.detail', 'contract_id', store=True,
                                     compute='_compute_rental_details', string="租金明细", readonly=False, copy=False)
    rental_details_archived = fields.One2many(comodel_name='estate.lease.contract.property.rental.detail',
                                              inverse_name='contract_id',
                                              string="租金明细(已归档)")

    property_ini_img_ids = fields.One2many(comodel_name='estate.lease.contract.property.ini.state',
                                           inverse_name='contract_id', string="资产初始状态图",
                                           compute="_compute_property_ini_img_ids")
    property_ini_img_ids_readonly = fields.Boolean(string="资产初始状态图只读", default=True, store=False,
                                                   compute="_compute_property_ini_img_ids_readonly")

    heat_fee_setting = fields.Many2one(comodel_name="estate.lease.contract.heat.fee.setting", string="供暖费通知设置",
                                       compute="_get_heat_fee_setting", store=False)
    heat_fee_amount_cn = fields.Char(string="供暖费（大写）", compute="_compute_heat_fee_amount_cn", store=False)

    # todo 目前的业务上一个合同只有一个property，应该按照合同：租赁标的1对多的关系实现
    @api.depends("heat_fee_setting")
    def _compute_heat_fee_amount_cn(self):
        for record in self:
            if record.heat_fee_setting:
                heat_fee_amount = record.heat_fee_setting.heat_fee_price * record.property_ids[0].rent_area
                record.heat_fee_amount_cn = Utils.arabic_to_chinese(heat_fee_amount)
            else:
                record.heat_fee_amount_cn = False

    def _get_heat_fee_setting(self):
        for record in self:
            heat_fee_setting_id = self.env['estate.lease.contract.heat.fee.setting'].search([
                ('company_id', '=', record.company_id.id)], limit=1)
            if heat_fee_setting_id:
                record.heat_fee_setting = heat_fee_setting_id[0].id
            else:
                record.heat_fee_setting = False

    @api.depends("property_ids")
    def _compute_property_ini_img_ids(self):
        for record in self:
            tgt_ids = []
            res = self.env['estate.lease.contract.property.ini.state'].search([('contract_id', '=', record.id)])

            for rcd in res:
                if (not rcd.property_id) or (not rcd.image_1920) or \
                        (not record.property_ids) or (rcd.property_id not in record.property_ids):
                    rcd.unlink()
                else:
                    tgt_ids.append(rcd.id)
            if tgt_ids:
                record.property_ini_img_ids = self.env['estate.lease.contract.property.ini.state'].browse(tgt_ids)
            else:
                record.property_ini_img_ids = False

    @api.depends("property_ids")
    def _compute_property_ini_img_ids_readonly(self):
        for record in self:
            if record.property_ids:
                record.property_ini_img_ids_readonly = False
            else:
                record.property_ini_img_ids_readonly = True

    @api.onchange("registration_addr")
    def _check_registration_addr_duplicated(self):
        for record in self:
            if record.registration_addr:
                valid_contract_list = []
                for addr in record.registration_addr:
                    current_contracts = self._check_registration_addr_in_contract(addr.id, record)
                    for each_contract in current_contracts:
                        if each_contract.id != record.id:
                            if each_contract.state in ('released', 'to_be_released'):
                                valid_contract_list.append(
                                    f"注册地址：【 {addr.name}】合同：【{each_contract.name}】【{each_contract.contract_no}】"
                                    f"承租人：【 {each_contract.renter_id.name}】"
                                    f"租赁期间：【{each_contract.date_rent_start}~{each_contract.date_rent_end}】")

                if valid_contract_list:
                    msg = '；'.join(valid_contract_list)
                    raise UserError(_('注册地址已分配其他合同：{0}'.format(msg)))

    @api.depends("registration_addr")
    def _compute_registration_addr_count(self):
        for record in self:
            record.registration_addr_count = 0
            record.registration_addr_sum = 0
            for addr in record.registration_addr:
                record.registration_addr_count += 1
                record.registration_addr_sum = record.registration_addr_sum + addr.price

    @api.depends("contract_no")
    def _compute_edit_on_hist_page(self):
        editable = False
        if 'contract_read_only' in self.env.context:
            editable = self.env.context.get('contract_read_only')
            _logger.info(f"self.env.context.get('contract_read_only')={editable}")

        """合同管理员希望在合同发布后，在查看界面也可以随时修改"""
        if self.env.user.has_group('estate_lease_contract.estate_lease_contract_group_manager'):
            _logger.info(f"有estate_lease_contract_group_manager权限")
            editable = True
            # 还要看看是否已过期和失效合同
            for record in self:
                _logger.info(f"合同状态record.state={record.state}")
                if record.state != 'invalid':
                    editable = True
                else:
                    editable = False
            _logger.info(f"有estate_lease_contract_group_manager权限,so editable={editable}")

        self.edit_on_hist_page = editable
        for record in self:
            record.edit_on_hist_page = editable

        return editable

    edit_on_hist_page = fields.Boolean(string='历史页面可编辑', default=lambda self: self._compute_edit_on_hist_page(),
                                       compute="_compute_edit_on_hist_page", store=False)
    parent_id = fields.Integer(string="续租前合同ID")

    @api.depends("property_ids", "rental_details")
    def _compute_rental_details(self):
        # 把计算结果付回给rental_details
        for record in self:
            tgt_id = record._origin.id if isinstance(record.id, models.NewId) else record.id
            _logger.info(f"_compute_rental_details called property_ids={record.property_ids.ids};contract={tgt_id}")
            rent_details = self.env['estate.lease.contract.property.rental.detail'].search(
                [('contract_id', '=', tgt_id), ('property_id', 'in', record.property_ids.ids)]).mapped('id')
            _logger.info(f"searched rental_details={len(rent_details)}条")
            record.rental_details = rent_details

    # 合同页面金额汇总标签页的刷新按钮动作
    def action_refresh_all_money(self):
        _logger.info(f"action_refresh_all_money called")
        self._compute_property_rental_detail_ids()
        self._compute_rental_details()
        self._compute_warn_msg()
        self._compute_property_ini_img_ids()

    # 刷新租金方案
    def action_refresh_rental_plan(self):
        _logger.info(f"action_refresh_rental_plan called")
        self._compute_rental_plan_ids()
        self.action_refresh_all_money()

    # 刷新物业费方案
    def action_refresh_management_fee_plan(self):
        self._compute_property_management_fee_plan_ids()

    # 根据租期和租金方案计算租金明细
    @api.depends("property_ids", "date_rent_start", "date_rent_end", "rental_plan_ids")
    def _compute_property_rental_detail_ids(self):
        for record in self:
            if record.date_rent_start and record.date_rent_end and record.property_ids and record.rental_plan_ids:
                generated_rental_details = _generate_details_from_rent_plan(record)
                # 先删除旧纪录
                _logger.info(f"删掉estate.lease.contract.property.rental.detail中contract_id={record.id}的not edit记录")
                self.env['estate.lease.contract.property.rental.detail'].search(
                    [('contract_id', '=', record.id), ('edited', '=', False)]).write({'active': False})
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
                        'edited': rental_detail['edited'],
                    })

    # 合同新建时默认不生效，需要手动修改
    active = fields.Boolean(default=False, copy=False, string="录入完成")
    # 合同状态
    state = fields.Selection(
        string='合同状态', tracking=True,
        selection=[('recording', '录入中未生效'), ('to_be_released', '已发布待生效'), ('released', '已发布已生效'),
                   ('invalid', '过期/失效')], default="recording", copy=False
    )

    # 合同终止状态
    terminated = fields.Boolean(default=False, copy=False, string="合同终止/退租")
    date_terminated = fields.Date(copy=False, string="合同终止/退租日")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    # 因租金明细修改后的警告提示信息
    warn_msg = fields.Text(string="提示", default="", store=False, compute="_compute_warn_msg")

    # 合同总计收缴状况统计
    contract_amount = fields.Float(string="合同总额（元）", compute="_compute_contract_amount", readonly=True, store=False)
    contract_concessions = fields.Float(string="合同总优惠（元）", readonly=True, store=False,
                                        compute="_compute_contract_amount")
    contract_receivable = fields.Float(string="合同总应收（元）", readonly=True, store=False,
                                       compute="_compute_contract_amount")
    contract_received = fields.Float(string="合同总实收（元）", readonly=True, store=False,
                                     compute="_compute_contract_amount")
    contract_remain = fields.Float(string="剩余总应收（元）", readonly=True, store=False,
                                   compute="_compute_contract_amount")
    contract_d_start_issue = fields.Date(string="本期开始日", readonly=True, store=False,
                                         compute="_compute_contract_amount")
    contract_d_end_issue = fields.Date(string="本期结束日", readonly=True, store=False,
                                       compute="_compute_contract_amount")
    contract_d_payment_issue = fields.Date(string="本期支付日", readonly=True, store=False,
                                           compute="_compute_contract_amount")
    contract_receivable_issue = fields.Float(string="本期应收（元）", readonly=True, store=False,
                                             compute="_compute_contract_amount")
    contract_received_issue = fields.Float(string="本期实收（元）", readonly=True, store=False,
                                           compute="_compute_contract_amount")
    contract_received_2_d_issue = fields.Date(string="实收至", readonly=True, store=False,
                                              compute="_compute_contract_amount")
    contract_arrears_issue = fields.Float(string="本期欠缴（元）", readonly=True, store=False,
                                          compute="_compute_contract_amount")

    @api.depends("rental_details")
    def _compute_contract_amount(self):
        _logger.debug("开始计算合同收款状况")
        for record in self:
            c_amount = 0.0
            c_concessions = 0.0
            c_receivable = 0.0
            c_received = 0.0
            c_remain = 0.0
            c_d_start_issue = None
            c_d_end_issue = None
            c_d_payment_issue = None
            c_receivable_issue = 0.0
            c_received_issue = 0.0
            c_received_2_d_issue = None
            c_arrears_issue = 0.0
            for rental_detail in record.rental_details:
                _logger.debug("按合同租金明细统计")
                c_amount += rental_detail.rental_amount if rental_detail.rental_amount else 0.0
                c_concessions += rental_detail.incentive_amount if rental_detail.incentive_amount else 0.0
                c_receivable += rental_detail.rental_receivable if rental_detail.rental_receivable else 0.0
                c_received += rental_detail.rental_received if rental_detail.rental_received else 0.0
                c_remain += rental_detail.rental_arrears if rental_detail.rental_arrears else 0.0
                # 当有多条租赁标的时，这里只取最后一条
                date_s = rental_detail.date_payment if rental_detail.date_payment else rental_detail.period_date_from
                if date_s <= fields.Date.today() <= rental_detail.period_date_to:
                    c_d_start_issue = rental_detail.period_date_from
                    c_d_end_issue = rental_detail.period_date_to
                    c_d_payment_issue = rental_detail.date_payment
                    c_receivable_issue = rental_detail.rental_receivable
                    c_received_issue = rental_detail.rental_received
                    c_received_2_d_issue = rental_detail.rental_received_2_date
                    c_arrears_issue = rental_detail.rental_arrears

            record.contract_amount = c_amount
            record.contract_concessions = c_concessions
            record.contract_receivable = c_receivable
            record.contract_received = c_received
            record.contract_remain = c_remain
            record.contract_d_start_issue = c_d_start_issue
            record.contract_d_end_issue = c_d_end_issue
            record.contract_d_payment_issue = c_d_payment_issue
            record.contract_receivable_issue = c_receivable_issue
            record.contract_received_issue = c_received_issue
            record.contract_received_2_d_issue = c_received_2_d_issue
            record.contract_arrears_issue = c_arrears_issue

    @api.depends("rental_details", "property_ids")
    def _compute_warn_msg(self):
        for record in self:
            record.warn_msg = ""
            # 是否有重复明细数据
            combination_counts = {}
            for detail in record.rental_details:
                combination = (detail.property_id.name,
                               f"开始：{detail.period_date_from}", f"结束：{detail.period_date_to}")
                if combination in combination_counts:
                    combination_counts[combination] += 1
                else:
                    combination_counts[combination] = 1

            duplicates = {k: v for k, v in combination_counts.items() if v > 1}
            if duplicates:
                for combi, cnt in duplicates.items():
                    record.warn_msg += f"{combi}出现{cnt}次；"

                record.warn_msg += f"这种情况一般是由于修改了租金明细数据后重新生成租金明细数据而造成的。" \
                                   f"请根据实际情况调整或删除租金明细。" \
                                   f"一般情况下应删除掉新生成的本期数据（黑色行），而保留修改过的数据（红色行）。"

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
                                    if each_contract.state in ('released', 'to_be_released'):
                                        current_contract_list.append(
                                            f"房屋：【 {property_id.name}】合同：【{each_contract.name}】"
                                            f"承租人：【 {each_contract.renter_id.name}】"
                                            f"租赁期间：【{each_contract.date_rent_start}~{each_contract.date_rent_end}】")

                if current_contract_list:
                    msg = '；'.join(current_contract_list)
                    raise UserError(_('不能发布本合同，因为房屋在其他租赁合同中租赁期重叠：{0}'.format(msg)))

            else:
                raise UserError(_('发布合同需要至少绑定一个租赁标的'))

            if record.date_rent_start and record.date_start and record.date_rent_start < record.date_start:
                record.date_start = record.date_rent_start
                # raise UserError("合同开始日期不能晚于计租开始日期！")

            # 发布时最终做校验
            self._check_registration_addr_duplicated()

            record.active = True
            # 根据合同生效日期判断state
            depend_date = record.date_start
            if record.property_state_by_date_sign:
                depend_date = record.date_sign
            if record.property_state_by_date_start:
                depend_date = record.date_start
            if record.property_state_by_date_rent_start:
                depend_date = record.date_rent_start

            # 合同状态
            if record.date_start <= date.today():
                record.state = 'released'
            else:
                record.state = 'to_be_released'

            if depend_date <= date.today():
                for each_property in record.property_ids:
                    if each_property.state != "sold":
                        each_property.state = "sold"
            else:
                for each_property in record.property_ids:
                    if each_property.state != "offer_accepted":
                        each_property.state = "offer_accepted"

            if record.date_rent_end < date.today():
                for each_property in record.property_ids:
                    if each_property.state != "out_dated":
                        each_property.state = "out_dated"
                record.state = 'invalid'

    # 取消发布合同
    def action_cancel_release_contract(self):
        for record in self:
            record.active = False
            record.state = 'recording'
            for each_property in record.property_ids:
                if each_property.state != "offer_received":
                    each_property.state = "offer_received"

            # 跳转至form录入界面
            action = self._goto_recording_form(record.id)
            return action

    @api.constrains('property_ids')
    def _check_update(self):
        for record in self:
            if record.state in ['to_be_released', 'released']:
                self.action_release_contract()

    def _insert_contract_registration_addr_rel(self, records):
        if records:
            tgt_rcd = records
        else:
            tgt_rcd = self

        contract_registration_addr_rel = []
        for rcd in tgt_rcd:
            for addr in rcd.registration_addr:
                contract_registration_addr_rel.append({
                    "name": [rcd.name, addr.name,
                             addr.party_b_associated_company.name if addr.party_b_associated_company else ""],
                    "price": addr.price,
                    "sequence": addr.sequence,
                    "contract_id": rcd.id,
                    "registration_addr_id": addr.id,
                    "party_b_associated_company_id":
                        addr.party_b_associated_company.id if addr.party_b_associated_company else None,
                    "company_id": self.env.user.company_id.id,
                })
        if contract_registration_addr_rel:
            self.env['estate.lease.contract.registration.addr.rel'].create(contract_registration_addr_rel)

    def _insert_contract_property_rental_plan_rel(self, records):
        _logger.info(f"进入 _insert_contract_property_rental_plan_rel 方法")
        create_new = False
        if records:
            rgt_rcd = records
            create_new = True
        else:
            rgt_rcd = self
            create_new = False

        contract_rental_plan_rel = []
        for record in rgt_rcd:

            for each_property in record.property_ids:
                contract_rent_amount_monthly = each_property.rent_amount_monthly_adjust \
                    if each_property.rent_amount_monthly_adjust else each_property.rent_amount_monthly_auto
                contract_rent_amount_yearly = each_property.rent_amount_yearly_adjust \
                    if each_property.rent_amount_yearly_adjust_4_view else contract_rent_amount_monthly * 12

                contract_rental_plan_rel.append({
                    "contract_id": record.id,
                    "property_id": each_property.id,
                    "rental_plan_id": each_property.rent_plan_id.id if each_property.rent_plan_id.id else None,
                    "company_id": self.env.user.company_id.id,
                    "contract_property_name": each_property.name,
                    "contract_property_state": each_property.state,
                    "contract_property_area": each_property.rent_area,
                    "contract_property_building_area": each_property.building_area,
                    "contract_deposit_months": each_property.deposit_months,
                    "contract_deposit_amount": each_property.deposit_amount,
                    "deposit_receivable": each_property.deposit_amount,
                    "contract_rent_amount_monthly": contract_rent_amount_monthly,
                    "contract_rent_amount_year": contract_rent_amount_yearly,
                    "contract_rent_payment_method": each_property.latest_payment_method,
                })

        if contract_rental_plan_rel:
            if create_new:
                self.env['estate.lease.contract.rental.plan.rel'].create(contract_rental_plan_rel)
            else:
                for rel_data in contract_rental_plan_rel:
                    search_domain = [('contract_id', '=', rel_data["contract_id"]),
                                     ('property_id', '=', rel_data["property_id"]),
                                     ('rental_plan_id', '=', rel_data["rental_plan_id"])]
                    search_rst = self.env['estate.lease.contract.rental.plan.rel'].search(search_domain)
                    if search_rst:
                        search_rst.write(rel_data)
                    else:
                        search_rst.create(rel_data)

        # 界面上操作了删除的租赁标的
        for record in self:
            del_domain = [('contract_id', '=', record.id)]
            rel_rcd_exist = self.env['estate.lease.contract.rental.plan.rel'].search(del_domain)
            for old_rcd in rel_rcd_exist:
                old_rcd_exist = False
                for new_rcd in contract_rental_plan_rel:
                    if old_rcd.property_id.id == new_rcd["property_id"]:
                        old_rcd_exist = True
                        continue
                if not old_rcd_exist:
                    _logger.info(f"删除old_rcd={old_rcd}")
                    old_rcd.unlink()

    @api.model
    def create(self, vals):
        # 将contract_id,property_id,rental_plan_id 写进 estate.lease.contract.rental.plan.rel 表
        if 'date_rent_start' in vals and 'date_start' in vals and vals['date_rent_start'] and vals['date_start'] and \
                vals['date_rent_start'] < vals['date_start']:
            vals['date_start'] = vals['date_rent_start']
            # raise UserError("合同开始日期不能晚于计租开始日期！")

        records = super().create(vals)

        self._insert_contract_property_rental_plan_rel(records)
        self._insert_contract_registration_addr_rel(records)

        return records

    @api.model
    def write(self, vals):
        _logger.info(f"write1 vals=：{vals}")

        for record in self:
            _logger.info(f"write1 record=个数：{len(record.rental_details)}-{record.rental_details}")

            if 'date_start' in vals:
                if vals['date_start']:
                    if 'date_rent_start' in vals:
                        if vals['date_rent_start']:
                            if vals['date_rent_start'] < vals['date_start']:
                                vals['date_start'] = vals['date_rent_start']
                                # raise UserError("合同开始日期不能晚于计租开始日期！")
                    else:
                        if record.date_rent_start:
                            if isinstance(vals['date_start'], str):
                                if record.date_rent_start < datetime.strptime(vals['date_start'], '%Y-%m-%d').date():
                                    vals['date_start'] = record.date_rent_start.strftime('%Y-%m-%d')
                            if isinstance(vals['date_start'], date):
                                if record.date_rent_start < vals['date_start']:
                                    vals['date_start'] = record.date_rent_start
                                # raise UserError("合同开始日期不能晚于计租开始日期！")

            if 'date_rent_start' in vals:
                if vals['date_rent_start']:
                    if 'date_start' in vals:
                        if vals['date_start']:
                            if vals['date_rent_start'] < vals['date_start']:
                                vals['date_start'] = vals['date_rent_start']
                                # raise UserError("合同开始日期不能晚于计租开始日期！")
                    else:
                        if record.date_start:
                            if isinstance(vals['date_rent_start'], str):
                                if datetime.strptime(vals['date_rent_start'], '%Y-%m-%d').date() < record.date_start:
                                    record.date_start = datetime.strptime(vals['date_rent_start'], '%Y-%m-%d').date()
                            if isinstance(vals['date_rent_start'], date):
                                if vals['date_rent_start'] < record.date_start:
                                    record.date_start = vals['date_rent_start']
                                # raise UserError("合同开始日期不能晚于计租开始日期！")

            if ('date_start' not in vals) and ('date_rent_start' not in vals):
                if record.date_rent_start and record.date_start and record.date_rent_start < record.date_start:
                    record.date_start = record.date_rent_start
                    # raise UserError("合同开始日期不能晚于计租开始日期！")

        res = super().write(vals)
        _logger.info(f"write2 vals=：{vals}")
        for record in self:
            _logger.info(f"write2 record=个数：{len(record.rental_details)}-{record.rental_details}")

        # 避免手调sequence时，大量日志输出
        if "sequence" in vals and len(vals) == 1:
            _logger.info(f"不更新合同-资产-租金方案历史表、不更新合同-注册地址历史表")
        else:
            # 合同-资产-租金方案历史表
            """押金分次收缴表estate_lease_contract_property_deposit是合同资产方案关系表contract_property_rental_plan_rel的子表
            押金收缴子表写入数据时依赖关系父表的id，所以不能采用上述删除→创建的方式，改为采用更新的方式"""
            # self._delete_contract_property_rental_plan_rel()
            self._insert_contract_property_rental_plan_rel(None)

            # 合同-注册地址历史表
            self._delete_contract_registration_addr_rel()
            self._insert_contract_registration_addr_rel(None)

        return res

    def _delete_contract_registration_addr_rel(self):
        for record in self:
            self.env['estate.lease.contract.registration.addr.rel'].search([('contract_id', '=', record.id)]).unlink()

    def _delete_contract_property_rental_plan_rel(self):

        for record in self:
            self.env['estate.lease.contract.rental.plan.rel'].search([('contract_id', '=', record.id)]).unlink()

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_needed(self):
        _logger.info(f"开始删除……")
        for record in self:
            _logger.info(f"contract id={record.id},state={record.state},active={record.active}")
            if record.state != 'recording':
                raise UserError(_(f'本合同目前所处状态：{record.state}，不能删除'))

            self.compute_property_state(record.property_ids)

    # 手动续租
    def action_contract_renewal(self):
        # 续租，延用字段：
        default = {
            "contract_no": f"{self.contract_no}-xz-01",
            "date_rent_start": self.date_rent_end + timedelta(days=1),
            "date_rent_end": self.date_rent_end + timedelta(days=1) + (self.date_rent_end - self.date_rent_start),
            "parent_id": self.id,
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

        # 续租不收押金，设置之前要判断当前日期是否在当前合同的租赁期间内！！！设置后，该资产的这些属性就影响所有历史合同中的该资产了，所以，理论上
        # 修改对象应该是合同中的资产（另作一张表来存）而不应该是直接修改资产master。这也意味着，合同做成/修改时，只要不修改资产的基础信息，那么
        # 业务上来说，针对该资产的修改内容应该针对的是这张保存了合同-资产的新表中的资产信息
        for rcd in new_record:
            for property_id in rcd.property_ids:
                property_id.deposit_months = 0
                property_id.deposit_amount = 0
        new_record.lease_deposit = 0

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

    def _get_contract_no(self, last_write):
        _logger.info("开始计算合同编号")
        prefix_str = "ZCZL-HT-"

        formatted_date = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d-%H%M%S')
        random_number = '{:03d}'.format(random.randint(0, 999))
        str_ret = prefix_str + formatted_date + '-' + random_number
        _logger.info(f"str_ret=[{str_ret}]")

        return str_ret

    def _get_default_date_rent_end(self):
        return _get_period_total_e(fields.Date.from_string(fields.Date.context_today(self)), 12, False)

    def _get_default_name(self):
        contract_name = "房屋租赁合同"
        self_company = self.env.user.company_id
        contract_name = f"{self_company.name}{contract_name}"
        if self_company.id == 3:
            if "四九一" in self_company.name:
                contract_name = "491空间房屋租赁合同"

        return contract_name

    """@api.model
    private_search应该是 _search 属于系统底层函数，在tree、form、create、update等很多场景下有调用，控制逻辑太复杂，不建议触碰底层函数
    """

    def private_search(self, domain, *args, is_from_self=None, **kwargs):

        _logger.info(f"search domain={domain}")
        _logger.info(f"search args={args}")
        _logger.info(f"search kwargs={kwargs}")
        if is_from_self:
            return super()._search(domain, *args, **kwargs)

        # 针对非list的场景
        if len(domain) == 1:
            for token in domain:
                left, operator, right = token
                if left == 'id' and operator == '=':
                    _logger.info(f"直接返回了")
                    return super()._search(domain, *args, **kwargs)

        if not self.env.context.get('contract_read_only') or self.env.context.get('contract_read_only') is False:
            return super()._search(domain, *args, **kwargs)

        # 当进行分组时，应以租赁标的为基础筛选无效合同
        tgt_property_ids = []
        for token in domain:
            if len(token) == 3:
                left, operator, right = token
                if left == 'property_ids':
                    tgt_property_ids.append(right)
        var_temp = 0 if tgt_property_ids else 1
        # 先做好条件1=1，然后防止 in (空) 出错
        if not tgt_property_ids:
            tgt_property_ids = [-1]
        # 已经过期的合同不显示，但是希望那些虽然已经过期无效，但是由于有续租而为了显示连续性而继续保留显示，即使不是续租，原租户继续租原房也行
        # 先选出已失效合同
        self.env.cr.execute("""
                            SELECT t_c.id, t_c.renter_id, t_r.property_id 
                            FROM estate_lease_contract t_c, contract_property_rel t_r 
                            WHERE t_c.company_id = %s 
                              AND (t_c.terminated IS NULL or t_c.terminated IS FALSE) 
                              AND t_c.active IS TRUE 
                              AND t_c.state = 'invalid' 
                              AND t_c.renter_id IS not NULL 
                              AND t_c.id = t_r.contract_id 
                              AND (1 = %s or t_r.property_id in %s) 
                            ORDER BY t_r.property_id, t_c.renter_id, t_c.date_rent_end DESC
                """, [self.env.user.company_id.id, var_temp, tuple(tgt_property_ids)])
        invalid_rcds = self.env.cr.fetchall()
        valid_ids = []
        _logger.info(f"invalid_rcds={invalid_rcds}")

        for contract_id, renter_id, property_id in invalid_rcds:
            self.env.cr.execute("""
                SELECT COUNT(1) FROM estate_lease_contract t_c, contract_property_rel t_r
                WHERE t_c.company_id = %s
                  AND (t_c.terminated IS NULL or t_c.terminated IS FALSE)
                  AND t_c.active IS TRUE
                  AND t_c.state in ('released', 'to_be_released')
                  AND (t_c.renter_id = %s and t_c.renter_id is not NULL) 
                  AND t_r.property_id = %s
                  AND t_c.id = t_r.contract_id
            """, (self.env.user.company_id.id, renter_id, property_id))

            valid_rcds = self.env.cr.dictfetchone()['count']
            _logger.info(f"回查的valid_rcds={valid_rcds}")
            if valid_rcds > 0:
                valid_ids.append(contract_id)

        _logger.info(f"原domain={domain}")
        _logger.info(f"补充的valid_ids={valid_ids}")

        if valid_ids:
            ids_origin = self.env['estate.lease.contract']._search(domain, *args, is_from_self=True, **kwargs)
            valid_domain = [('id', 'in', valid_ids)]
            ids_added = self.env['estate.lease.contract']._search(valid_domain, *args, is_from_self=True, **kwargs)
            return super()._search(['|', ('id', 'in', ids_origin), ('id', 'in', ids_added)], *args, **kwargs)
        else:
            return super()._search(domain, *args, **kwargs)

    def _goto_recording_form(self, self_id):
        title = "资产租赁合同（取消发布，重新录入）"
        # 设置上下文
        context = {
            'search_default_active': False,
            'contract_read_only': False,
            'menu_root': 'estate.lease.contract'
        }
        # 设置域
        domain = [('id', '=', self_id), ('active', '=', False)]

        # 跳转到新记录的表单视图
        return self._action_view_record(self_id, title, context, domain)

    def compute_property_state(self, property_ids):
        # 更新该合同下的每个资产状态
        for each_property in property_ids:
            contracts = self.env['estate.lease.contract'].search([('property_ids', 'in', each_property.id)],
                                                                 order="date_rent_end ASC")
            if not contracts:
                if each_property.state != 'canceled':
                    each_property.state = 'canceled'
                break

            # 由于数据从旧到新排列，且已发布的资产租赁数据不会有时间段重合
            for contract in contracts:
                # 先看覆盖当天日期的时间段，最优先判断
                if contract.date_start <= fields.Date.context_today(self) <= contract.date_rent_end:
                    # 合同开始，但是租期未开始
                    if contract.date_start <= fields.Date.context_today(self) < contract.date_rent_start:
                        # 合同已发布且未终止
                        if contract.active and not contract.terminated:
                            if contract.state in ('to_be_released', 'released'):
                                if each_property.state != "offer_accepted":
                                    each_property.state = "offer_accepted"
                            elif contract.state == "recording":
                                if each_property.state != "offer_received":
                                    each_property.state = "offer_received"
                            elif contract.state == "invalid":
                                if each_property.state != "canceled":
                                    each_property.state = "canceled"
                            else:
                                _logger.error(f"新定义的合同状态{contract.state}，需增加逻辑")
                                pass
                        elif contract.active and contract.terminated:
                            if each_property.state != "canceled":
                                each_property.state = "canceled"
                        elif (not contract.active) and (not contract.terminated):
                            # 目前资产状态判断依据只有这三个：date_sign、date_start、date_rent_start
                            if contract.property_state_by_date_sign or contract.property_state_by_date_start:
                                if each_property.state != "sold":
                                    each_property.state = "sold"
                            if contract.property_state_by_date_rent_start:
                                if each_property.state != "offer_received":
                                    each_property.state = "offer_received"
                        elif (not contract.active) and contract.terminated:
                            if each_property.state != "canceled":
                                each_property.state = "canceled"
                        else:
                            _logger.error(f"理论上不存在该情况：contract.active={contract.active};"
                                          f"contract.terminated={contract.terminated}")
                            pass
                    # 当前日期在租期内
                    else:
                        # 合同已发布且未终止
                        if contract.active and not contract.terminated:
                            if contract.state in ('to_be_released', 'released'):
                                if each_property.state != "sold":
                                    each_property.state = "sold"
                            elif contract.state == "recording":
                                if each_property.state != "offer_received":
                                    each_property.state = "offer_received"
                            elif contract.state == "invalid":
                                if each_property.state != "canceled":
                                    each_property.state = "canceled"
                            else:
                                _logger.error(f"新定义的合同状态{contract.state}，需增加逻辑")
                                pass
                        elif contract.active and contract.terminated:
                            if each_property.state != "canceled":
                                each_property.state = "canceled"
                        elif (not contract.active) and (not contract.terminated):
                            if each_property.state != "offer_received":
                                each_property.state = "offer_received"
                        elif (not contract.active) and contract.terminated:
                            if each_property.state != "canceled":
                                each_property.state = "canceled"
                        else:
                            _logger.error(f"理论上不存在该情况：contract.active={contract.active};"
                                          f"contract.terminated={contract.terminated}")
                            pass
                    # 当前最新状态最优先，所以有了就退出
                    break
                # 看未来数据:已签约但是尚未开始合同
                elif contract.date_sign <= fields.Date.context_today(self) < contract.date_start:
                    # 合同已发布且未终止
                    if contract.active and not contract.terminated:
                        if contract.state in ('released', 'to_be_released'):
                            if contract.property_state_by_date_sign:
                                if each_property.state != "sold":
                                    each_property.state = "sold"
                            if contract.property_state_by_date_start or contract.property_state_by_date_rent_start:
                                if each_property.state != "offer_accepted":
                                    each_property.state = "offer_accepted"
                        elif contract.state == "recording":
                            if each_property.state != "offer_received":
                                each_property.state = "offer_received"
                        elif contract.state == "invalid":
                            if each_property.state != "canceled":
                                each_property.state = "canceled"
                        else:
                            _logger.error(f"新定义的合同状态{contract.state}，需增加逻辑")
                            pass
                    elif contract.active and contract.terminated:
                        if each_property.state != "canceled":
                            each_property.state = "canceled"
                    elif (not contract.active) and (not contract.terminated):
                        if each_property.state != "offer_received":
                            each_property.state = "offer_received"
                    elif (not contract.active) and contract.terminated:
                        if each_property.state != "canceled":
                            each_property.state = "canceled"
                    else:
                        _logger.error(f"理论上不存在该情况：contract.active={contract.active};"
                                      f"contract.terminated={contract.terminated}")
                        pass
                    # 已看到未来数据，不用再看接下来的未来数据
                    break

                # 理论上不应该存在当前日期在签约日期之前的情况
                elif fields.Date.context_today(self) < contract.date_sign:
                    # 合同已发布且未终止
                    if contract.active and not contract.terminated:
                        if contract.state in ('released', 'to_be_released'):
                            if each_property.state != "offer_accepted":
                                each_property.state = "offer_accepted"
                        elif contract.state == "recording":
                            if each_property.state != "offer_received":
                                each_property.state = "offer_received"
                        elif contract.state == "invalid":
                            if each_property.state != "canceled":
                                each_property.state = "canceled"
                        else:
                            _logger.error(f"新定义的合同状态{contract.state}，需增加逻辑")
                            pass
                    elif contract.active and contract.terminated:
                        if each_property.state != "canceled":
                            each_property.state = "canceled"
                    elif (not contract.active) and (not contract.terminated):
                        if each_property.state != "offer_received":
                            each_property.state = "offer_received"
                    elif (not contract.active) and contract.terminated:
                        if each_property.state != "canceled":
                            each_property.state = "canceled"
                    else:
                        _logger.error(f"理论上不存在该情况：contract.active={contract.active};"
                                      f"contract.terminated={contract.terminated}")
                        pass
                    # 已看到未来数据，不用再看接下来的未来数据
                    break

                # 看过去的数据
                elif fields.Date.context_today(self) > contract.date_rent_end:
                    # 合同已发布且未终止
                    if contract.active and not contract.terminated:
                        if contract.state in ('to_be_released', 'released'):
                            if each_property.state != "out_dated":
                                each_property.state = "out_dated"
                        elif contract.state == "recording":
                            if each_property.state != "offer_received":
                                each_property.state = "offer_received"
                        elif contract.state == "invalid":
                            if each_property.state != "out_dated":
                                each_property.state = "out_dated"
                        else:
                            _logger.error(f"新定义的合同状态{contract.state}，需增加逻辑")
                            pass
                    elif contract.active and contract.terminated:
                        if each_property.state != "canceled":
                            each_property.state = "canceled"
                    elif (not contract.active) and (not contract.terminated):
                        if each_property.state != "offer_received":
                            each_property.state = "offer_received"
                    elif (not contract.active) and contract.terminated:
                        if each_property.state != "out_dated":
                            each_property.state = "out_dated"
                    else:
                        _logger.error(f"理论上不存在该情况：contract.active={contract.active};"
                                      f"contract.terminated={contract.terminated}")
                        pass
                    # 这里不能break，因为后边可能还有数据

    def download_all_images(self):
        action = {
            "type": "ir.actions.act_url",
            "url": "/estate_lease_contract/download/all_images/" + str(self.id),
            "target": "self",
        }
        return action

    def action_archive(self):

        if self.state == "recording" or not self.active:
            raise UserError("录入中合同不可归档，可直接删除！")

        # 只有已发布且未终止的合同才需要退租/终止
        if self.state in ('released', 'to_be_released') and not self.terminated:
            res = super().action_archive()

            self.active = True
            self.terminated = True
            self.date_terminated = fields.Date.context_today(self)
            self.state = "invalid"
            # 去除无用的租金明细
            search_domain = [('contract_id', 'in', self.ids), ('active', '=', False)]
            rental_details = self.env['estate.lease.contract.property.rental.detail'].search(search_domain)
            _logger.info(f"先删除无用的租金明细:{rental_details}")
            rental_details.unlink()

            # ↓↓↓由于合同状态通过state字段和terminated字段来控制，而active一直保持true，所以不能将租金明细设置为false
            # # 再将有效的租金明细设置为inactive
            # self.rental_details.active = False
            # 注册地址的重复使用判断时，也考虑到了合同的terminated，所以这里也不需要设置false
            # self.contract_registration_addr_rel_id.active = False
        else:
            # 已经处于归档状态的合同，要恢复提档的数据，应将其设置为录入中
            res = self.action_unarchive()

        return res

    def action_unarchive(self):

        res = super().action_unarchive()

        self.active = False
        self.state = "recording"
        self.terminated = False

        # 因为从未将其设置为False，所以无需多此一举
        # self.rental_details.active = True
        # self.contract_registration_addr_rel_id.active = True

        return res

    def terminate_tgt_contract(self, context):
        _logger.info(f"context={context}")
        terminate_target_contract_id = context.get('id')
        _logger.info(f"terminate_target_contract_id={terminate_target_contract_id}")
        search_domain = [('contract_id', '=', terminate_target_contract_id), ('active', '=', False)]
        rental_details = self.env['estate.lease.contract.property.rental.detail'].search(search_domain)
        _logger.info(f"终止合同签，先删除无用的租金明细:{rental_details}")
        rental_details.unlink()
        # 设置合同终止状态
        tgt_contract = self.env['estate.lease.contract'].search([('id', '=', terminate_target_contract_id)])
        tgt_contract.terminated = True
        tgt_contract.date_terminated = fields.Date.context_today(self)
        tgt_contract.state = "invalid"

    def print_heat_notice(self):
        return self.env.ref('estate_lease_contract.action_print_heat_fee_notice').report_action(self)
