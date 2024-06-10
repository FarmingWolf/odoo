# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from typing import Dict, List

from odoo import fields, models, api


class EstateLeaseContractPropertyExtend(models.Model):

    _description = "资产租赁合同租赁标的"
    _inherit = ['estate.property']

    rent_plan_id = fields.Many2one('estate.lease.contract.rental.plan', string="租金方案")
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
    rent_price = fields.Char(string="租金单价（元/月/㎡）", readonly=True, compute="_get_rent_plan_info")
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
                record.payment_date = ""
                record.compensation_method = ""
                record.compensation_period = ""

    @api.model
    def _format_m2m_values(self, records):

        formatted_values = []
        for record in records:
            formatted_values.append(f"{record.name}：{record.name_description}")
        return '； '.join(formatted_values)
