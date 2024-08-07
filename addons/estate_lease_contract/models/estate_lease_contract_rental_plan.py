# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import math

from odoo import fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateLeaseContractRentalPlan(models.Model):
    _name = "estate.lease.contract.rental.plan"
    _description = "资产租赁合同租金方案"
    _order = "name"

    name = fields.Char('资产租赁合同租金方案', required=True, copy=False, default="租金方案名-请重命名")
    rent_targets = fields.One2many("estate.property", "rent_plan_id", string='对应标的')
    business_method_id = fields.Selection(string="经营性质",
                                          selection=[('direct_sale', '直营'), ('franchisee', '加盟'),
                                                     ('agent', '代理'), ('direct_and_agent', '直营+代理'),
                                                     ('direct_and_franchisee', '直营+加盟')], )

    business_type_id = fields.Many2one("estate.lease.contract.rental.business.type", string="经营业态")
    main_category = fields.Many2one("estate.lease.contract.rental.main.category", string="主品类")

    billing_method = fields.Selection(string='计费方式', required=True,
                                      selection=[('by_fixed_price', '固定金额'), ('by_percentage', '纯抽成'),
                                                 ('by_progress', '按递增率'),
                                                 ('by_fixed_price_percentage_higher', '保底抽成两者取高')], )

    billing_progress_method_id = fields.Selection(string='递进方式',
                                                  selection=[('by_period', '按时间段'), ('by_turnover', '按营业额'),
                                                             ('no_progress', '无递增')], )

    period_percentage_id = fields.Many2many('estate.lease.contract.rental.period.percentage',
                                            'rental_plan_period_percentage_rel', 'rental_plan_id',
                                            'period_percentage_id',
                                            string='期间段递增率详情')

    turnover_percentage_id = fields.Many2many('estate.lease.contract.rental.turnover.percentage',
                                              'rental_plan_percentage_rel', 'rental_plan_id', 'turnover_percentage_id',
                                              string='营业额抽成详情')

    payment_period = fields.Selection(string="支付周期", required=True,
                                      selection=[('1', '月付'), ('2', '双月付'), ('3', '季付'),
                                                 ('4', '四个月付'), ('6', '半年付'), ('12', '年付')], )
    rent_price = fields.Float(default=0.0, string="租金单价（元/天/㎡）", digits=(12, 2))

    payment_date = fields.Selection(string="租金支付日", required=True,
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
                                        ('period_start_1_pay_this', '租期开始后的1日内付本期费用'), ], )

    compensation_method = fields.Selection(
        string='补差方式',
        selection=[('retreat_more_fill_less', '多退少补'), ('take_higher', '取高')], )

    compensation_period = fields.Selection(
        string='补差周期',
        selection=[('by_payment_period', '支付周期补差'), ('by_natural_half_year', '自然半年补差'),
                   ('by_natural_year', '自然年补差'), ('by_contract_year', '租约年补差')], )

    _sql_constraints = [
        ('name', 'unique(name)', '租金方案名不能重复')
    ]

    @api.model
    def create(self, vals_list):
        # 先做：按期间段递增率的检查，即 从第N月起的每X个月递增百分比，其他分支 todo
        _logger.info(f"vals_list={vals_list}")
        if "billing_method" in vals_list:
            if vals_list['billing_method'] == 'by_progress':
                if 'billing_progress_method_id' in vals_list:
                    if vals_list['billing_progress_method_id'] == 'by_period':
                        if 'period_percentage_id' not in vals_list:
                            raise UserError("请设置时间段递增规则详情!")
                        else:
                            if not vals_list['period_percentage_id']:
                                raise UserError("请设置时间段递增规则详情!")
                            else:
                                self._check_method_by_period(vals_list['period_percentage_id'])

        res = super().create(vals_list)
        return res

    def _check_method_by_period(self, methods_by_period):
        _logger.info(f"billing_progress_methods_by_period={methods_by_period}")
        methods_by_period_ids = []
        for method in methods_by_period:
            if len(method) == 2:
                methods_by_period_ids.append(method[1])

        record_sorted = self.env['estate.lease.contract.rental.period.percentage'].search([
            ('id', 'in', methods_by_period_ids)], order='billing_progress_info_month_from ASC')

        if not record_sorted or len(record_sorted) == 0:
            raise UserError("请设置时间段递增规则详情!")

        _logger.info(f"record_sorted={record_sorted}")

        i = 0
        for by_period_method in record_sorted:
            _logger.info(f"by_period_method={by_period_method}")
            if i > 0:
                df = by_period_method.billing_progress_info_month_from - \
                     record_sorted[i-1].billing_progress_info_month_from
                if math.fmod(df, by_period_method.billing_progress_info_month_every) != 0:
                    err_msg = f"期间段递增率明细设置有误！\n" \
                              f"【{by_period_method.name}】与【{record_sorted[i-1].name}】的起始月相差月数：" \
                              f"{by_period_method.billing_progress_info_month_from} - " \
                              f"{record_sorted[i-1].billing_progress_info_month_from}={df}不是" \
                              f"{record_sorted[i-1].billing_progress_info_month_every}的整数倍，请调整！"

                    raise UserError(err_msg)

            i += 1

