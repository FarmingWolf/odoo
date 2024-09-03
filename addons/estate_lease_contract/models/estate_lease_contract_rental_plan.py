# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import math

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.netsvc import log

_logger = logging.getLogger(__name__)


def _check_is_period_percentage(vals):
    if "billing_method" in vals:
        if vals['billing_method'] == 'by_progress':
            if 'billing_progress_method_id' in vals:
                if vals['billing_progress_method_id'] == 'by_period':
                    if 'period_percentage_id' not in vals:
                        raise UserError("请设置时间段递增规则详情!")
                    else:
                        if not vals['period_percentage_id']:
                            raise UserError("请设置时间段递增规则详情!")
                        else:
                            return True
    return False


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
    rent_price = fields.Float(default=0.0, string="租金单价（元/天/㎡）")

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
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '租金方案名不能重复')
    ]

    @api.model
    def create(self, vals_list):
        _logger.info(f"vals_list={vals_list}")
        if _check_is_period_percentage(vals_list):
            self._check_method_by_period(vals_list['period_percentage_id'])
        else:
            pass  # 先做：按期间段递增率的检查，即 从第N月起的每X个月递增百分比，其他分支 todo

        res = super().create(vals_list)
        return res

    def _check_method_by_period(self, methods_by_period):
        _logger.info(f"billing_progress_methods_by_period={methods_by_period}")
        methods_by_period_ids = []
        for method in methods_by_period:
            if len(method) == 2:
                methods_by_period_ids.append(method[1])

        domain = [('id', 'in', methods_by_period_ids)]
        _logger.info(f"domain={domain}")
        record_sorted = self.env['estate.lease.contract.rental.period.percentage'].\
            search(domain, order='billing_progress_info_month_from ASC')

        if not record_sorted or len(record_sorted) == 0:
            raise UserError("请设置时间段递增规则详情!")

        _logger.info(f"record_sorted={record_sorted}")

        i = 0
        for by_period_method in record_sorted:
            _logger.info(f"by_period_method={by_period_method}")
            if i > 0:
                df = by_period_method.billing_progress_info_month_from - \
                     record_sorted[i - 1].billing_progress_info_month_from
                if df == 0 or math.fmod(df, by_period_method.billing_progress_info_month_every) != 0:
                    err_msg = f"期间段递增率明细设置有误！\n" \
                              f"【{by_period_method.name}】与【{record_sorted[i - 1].name}】的起始月相差月数：" \
                              f"{by_period_method.billing_progress_info_month_from} - " \
                              f"{record_sorted[i - 1].billing_progress_info_month_from}={df}" \
                              f"{'不是' if df > 0 else ''}" \
                              f"{record_sorted[i - 1].billing_progress_info_month_every if df > 0 else ''}" \
                              f"{'的整数倍，请调整！' if df > 0 else ''}"

                    raise UserError(err_msg)

            i += 1

    @api.model
    def write(self, vals):
        _logger.info(f"vals={vals}")
        _logger.info(f'old period_percentage_id={self.period_percentage_id}')
        # 修改方案之前，先判断该方案是否在已经发布的合同中
        self._check_used_in_released_contract(vals)

        # 先检查是否按时间段递增的设置
        if self._check_is_period_percentage_4_update(vals):
            tgt_period_percentage = list(self.period_percentage_id.ids)
            if 'period_percentage_id' in vals:
                for period_percentage in vals['period_percentage_id']:  # 目前看只有3：UNLINK和4：LINK
                    _logger.info(f"in for period_percentage={period_percentage}")
                    _logger.info(f"before +- tgt_period_percentage={tgt_period_percentage}")
                    if period_percentage[0] in (3, 2):
                        tgt_period_percentage.remove(period_percentage[1])
                        _logger.info(f"after - tgt_period_percentage={tgt_period_percentage}")
                    elif period_percentage[0] == 4:
                        tgt_period_percentage.append(period_percentage[1])
                        _logger.info(f"after + tgt_period_percentage={tgt_period_percentage}")
                    else:
                        raise UserWarning(f"时间段递增率受到了一种未知设置！{period_percentage}")

            period_percentage_2_check = [[0, item] for item in tgt_period_percentage]
            self._check_method_by_period(period_percentage_2_check)
        else:
            pass  # 先做：按期间段递增率的检查，即 从第N月起的每X个月递增百分比，其他分支 todo

        res = super().write(vals)
        return res

    def _check_is_period_percentage_4_update(self, vals):
        if ("billing_method" in vals and vals['billing_method'] == 'by_progress') or \
                ("billing_method" not in vals and self.billing_method == 'by_progress'):
            if ('billing_progress_method_id' in vals and vals['billing_progress_method_id'] == 'by_period') or \
                    ('billing_progress_method_id' not in vals and self.billing_progress_method_id == 'by_period'):
                if 'period_percentage_id' not in vals:
                    if not self.period_percentage_id:
                        raise UserError("请设置时间段递增规则详情!")
                    else:
                        return True
                else:
                    if not vals['period_percentage_id']:
                        raise UserError("请设置时间段递增规则详情!")
                    else:
                        return True

        return False

    # 已经发布的合同中用了此方案，那么就不让write了
    def _check_used_in_released_contract(self, vals):
        if len(vals) == 0:
            return

        if len(vals) == 1 and 'rent_targets' in vals:
            return

        for record in self:
            msg_list = []
            _logger.info(f'本方案id={record.id}')
            domain = [('rental_plan_id', '=', record.id), ('rental_plan_id', '!=', False)]
            contracts_rel = self.env['estate.lease.contract.rental.plan.rel'].search(domain)
            for contract_rel in contracts_rel:
                if contract_rel.contract_id.state in ('to_be_released', 'released'):
                    msg_list.append(
                        f"房屋：【 {contract_rel.property_id.name}】合同：【{contract_rel.contract_id.name}】"
                        f"【{contract_rel.contract_id.contract_no}】"
                        f"承租人：【 {contract_rel.contract_id.renter_id.name}】")

            if msg_list:
                msg = '；'.join(msg_list)
                raise UserError(f'不能修改本租金方案【{record.name}】，因为该方案已在其他已发布的租赁合同使用：{msg}。'
                                f'建议：新作一个租金方案；或者将已发布的合同取消发布后方可修改本租金方案。')
