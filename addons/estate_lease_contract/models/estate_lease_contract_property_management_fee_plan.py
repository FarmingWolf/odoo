# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyManagementFeePlan(models.Model):
    _name = "estate.lease.contract.property.management.fee.plan"
    _description = "资产租赁合同物业费方案"
    _order = "sequence DESC, id DESC"

    name = fields.Char('物业费方案', required=True, default=lambda self: self._get_default_name())
    sequence = fields.Integer('排序', default=1)
    estate_lease_contract = fields.Many2one('estate.lease.contract', string="租赁合同",
                                            default=lambda self: self._get_estate_lease_contract())
    estate_lease_contract_uuid = fields.Char(string="租赁合同UUID",
                                             default=lambda self: self._get_estate_lease_contract_uuid())
    estate_lease_contract_property = fields.Many2one('estate.property', string="租赁标的",
                                                     default=lambda self: self._get_estate_lease_contract_property())
    property_management_fee_price = fields.Float(default=0.0, string="单价（元/天/㎡）")
    property_management_fee_price_monthly = fields.Float(default=0.0, string="月费（元/月）")
    billing_progress_method_id = fields.Selection(string='递增方式', required=True, default='no_progress',
                                                  selection=[('no_progress', '无递增'), ('by_period', '按时间段递增')])
    date_start = fields.Date("物业费收取开始日", required=True, readonly=False,
                             default=lambda self: self._get_default_date_start(), store=True)
    date_start_depending = fields.Selection(string="物业费开始日", required=True,
                                            selection=[('date_sign', '合同签订日'), ('date_start', '合同开始日'),
                                                       ('date_rent_start', '租金开始日'),
                                                       ('date_other', '其他日期')], default='date_start')
    payment_period_depending = fields.Selection(string="物业费支付周期", default="same_with_rental", required=True,
                                                selection=[('same_with_rental', '同于租金支付周期'),
                                                           ('not_same_with_rental', '不同于租金支付周期')])
    payment_period = fields.Selection(string="支付周期", required=True, store=True, readonly=False,
                                      default=lambda self: self._get_default_payment_period(),
                                      selection=[('1', '月付'), ('2', '双月付'), ('3', '季付'),
                                                 ('4', '四个月付'), ('5', '五个月付'), ('6', '半年付'),
                                                 ('7', '七个月付'), ('8', '八个月付'), ('9', '九个月付'),
                                                 ('10', '十个月付'), ('11', '十一个月付'), ('12', '年付')])
    payment_date = fields.Selection(string="物业费支付日", required=True, store=True, readonly=False,
                                    default=lambda self: self._get_default_payment_date(),
                                    selection=[('period_start_30_bef_this', '租期开始日的30日前付本期费用'),
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

    period_percentage_id = fields.Many2many('estate.lease.contract.management.fee.period.percentage',
                                            'management_fee_plan_period_percentage_rel', 'management_fee_plan_id',
                                            'period_percentage_id',
                                            string='物业费期间段递增率详情')

    property_name = fields.Char('租赁标的', readonly=True, default=lambda self: self._get_property_name())
    rent_target_area = fields.Float(string="计租面积（㎡）", readonly=True,
                                    default=lambda self: self._get_default_rent_area(),
                                    compute="_compute_rent_target_area")

    # 按时间段递增的情况下：
    name_description = fields.Char(string="方案描述", compute="_get_name_description")
    rent_targets = fields.Many2one("estate.property", string='对应标的', related="estate_lease_contract_property")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    def _get_estate_lease_contract(self):
        if "default_estate_lease_contract" in self.env.context:
            return self.env.context.get("default_estate_lease_contract")

    def _get_estate_lease_contract_uuid(self):
        if 'contract_uuid_4_management_fee' in self.env.context:
            return self.env.context.get("contract_uuid_4_management_fee")

    def _get_estate_lease_contract_property(self):
        if 'default_estate_lease_contract_property' in self.env.context:
            return self.env.context.get("default_estate_lease_contract_property")

    def _get_default_payment_date(self):
        payment_date = 'period_start_15_bef_this' if not self.payment_date else self.payment_date
        for record in self:
            if record.payment_period_depending == 'same_with_rental':
                if 'payment_date_4_management_fee' in self.env.context:
                    payment_date = str(self.env.context.get('payment_date_4_management_fee'))
                else:
                    if request and request.session and 'payment_date_4_management_fee' in request.session:
                        payment_date = str(request.session.get('payment_date_4_management_fee'))

            if not record.payment_date or record.payment_date != payment_date:
                record.payment_date = payment_date

        return payment_date

    def _get_default_payment_period(self):
        _logger.info(f"self.payment_period={self.payment_period}")
        payment_period = '6' if not self.payment_period else self.payment_period
        for record in self:
            if record.payment_period_depending == 'same_with_rental':
                if 'payment_period_4_management_fee' in self.env.context:
                    payment_period = str(self.env.context.get('payment_period_4_management_fee'))
                else:
                    if request and request.session and 'payment_period_4_management_fee' in request.session:
                        payment_period = str(request.session.get('payment_period_4_management_fee'))

            if not record.payment_period or record.payment_period != payment_period:
                record.payment_period = payment_period

            _logger.info(f"self.payment_period={record.payment_period};payment_period={payment_period}")
        return payment_period

    def _get_property_name(self):
        property_name = ''
        if 'property_nm_4_management_fee' in self.env.context:
            property_name = str(self.env.context.get('property_nm_4_management_fee'))
        else:
            if request and request.session and 'property_nm_4_management_fee' in request.session:
                property_name = str(request.session.get('property_nm_4_management_fee'))

        return property_name

    def _get_default_name(self):
        fee_name = "物业费方案-" + fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d%H%M%S')
        property_name = self._get_property_name()
        if property_name:
            fee_name = property_name + "-" + fee_name

        return fee_name

    def _get_default_date_start(self):
        temp_date = fields.Date.context_today(self)
        for record in self:

            if record.date_start_depending == 'date_sign':
                temp_date = self.env.context.get('contract_date_sign_4_management_fee')
                return temp_date
            elif record.date_start_depending == 'date_start':
                temp_date = self.env.context.get('contract_date_start_4_management_fee')
                return temp_date
            elif record.date_start_depending == 'date_rent_start':
                temp_date = self.env.context.get('contract_date_rent_start_4_management_fee')
                return temp_date

        return temp_date

    @api.onchange("date_start")
    def _onchange_date_start(self):

        if fields.Date.from_string(self.date_start) == \
                fields.Date.from_string(self.env.context.get('contract_date_sign_4_management_fee')):
            if self.date_start_depending != 'date_sign':
                self.date_start_depending = 'date_sign'
        elif fields.Date.from_string(self.date_start) == \
                fields.Date.from_string(self.env.context.get('contract_date_start_4_management_fee')):
            if self.date_start_depending != 'date_start':
                self.date_start_depending = 'date_start'
        elif fields.Date.from_string(self.date_start) == \
                fields.Date.from_string(self.env.context.get('contract_date_rent_start_4_management_fee')):
            if self.date_start_depending != 'date_rent_start':
                self.date_start_depending = 'date_rent_start'
        else:
            if self.date_start_depending != 'date_other':
                self.date_start_depending = 'date_other'

    @api.onchange('date_start_depending')
    def _onchange_date_start_depending(self):
        temp_date = self._get_default_date_start()
        if self.date_start_depending in ['date_sign', 'date_start', 'date_rent_start']:
            if fields.Date.from_string(self.date_start) != fields.Date.from_string(temp_date):
                self.date_start = temp_date

    @api.onchange('payment_period', 'payment_date')
    def _onchange_payment_period_payment_date(self):
        if self.payment_period != self.env.context.get('payment_period_4_management_fee') or \
                self.payment_date != self.env.context.get('payment_date_4_management_fee'):
            if self.payment_period_depending != 'not_same_with_rental':
                self.payment_period_depending = 'not_same_with_rental'

    @api.onchange('payment_period_depending')
    def _onchange_payment_period_depending(self):
        if self.payment_period_depending == "same_with_rental":
            temp_payment_period = self._get_default_payment_period()
            if self.payment_period != temp_payment_period:
                self.payment_period = temp_payment_period

            temp_payment_date = self._get_default_payment_date()
            if str(self.payment_date) != str(temp_payment_date):
                self.payment_date = temp_payment_date

    def _get_default_rent_area(self):
        if 'rent_area_4_management_fee' in self.env.context:
            if self.env.context.get('rent_area_4_management_fee') > 0:
                return self.env.context.get('rent_area_4_management_fee')

        if request and request.session and 'rent_area_4_management_fee' in request.session:
            return request.session.get('rent_area_4_management_fee')

        return 0

    @api.depends_context('rent_area_4_management_fee')
    def _compute_rent_target_area(self):

        rent_target_area = self._get_default_rent_area()

        for record in self:
            record.rent_target_area = rent_target_area

    @api.onchange('property_management_fee_price')
    def _onchange_property_management_fee_price(self):
        one_year_days = self._get_one_year_days()
        if self.rent_target_area and self.rent_target_area > 0:
            if self.property_management_fee_price_monthly != \
                    self.property_management_fee_price * self.rent_target_area * one_year_days / 12:
                self.property_management_fee_price_monthly = \
                    self.property_management_fee_price * self.rent_target_area * one_year_days / 12

    @api.onchange('property_management_fee_price_monthly')
    def _onchange_property_management_fee_price_monthly(self):
        one_year_days = self._get_one_year_days()
        if self.rent_target_area and self.rent_target_area > 0:
            if self.property_management_fee_price != \
                    self.property_management_fee_price_monthly * 12 / one_year_days / self.rent_target_area:
                self.property_management_fee_price = \
                    self.property_management_fee_price_monthly * 12 / one_year_days / self.rent_target_area

    @api.depends("name", "property_management_fee_price", "property_management_fee_price_monthly",
                 "payment_date", "payment_period", "billing_progress_method_id", "period_percentage_id")
    def _get_name_description(self):
        if self:
            for record in self:
                if record:
                    if record.billing_progress_method_id == "no_progress":
                        record.name_description = f"{record.name}：物业费单价" \
                                                  f"{record.property_management_fee_price}元/天/㎡，" \
                                                  f"{record.property_management_fee_price_monthly}元/月，不递增。" \
                                                  f"支付周期：{record.payment_period}"
                    else:
                        record.name_description = f"{record.name}：物业费单价" \
                                                  f"{record.property_management_fee_price}元/天/㎡，" \
                                                  f"{record.property_management_fee_price_monthly}元/月，有递增。" \
                                                  f"支付周期：{record.payment_period}"

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '物业费方案名不能重复')
    ]

    @api.model
    def create(self, vals):
        record = super().create(vals)

        # if record.estate_lease_contract_property:
        #     if not record.estate_lease_contract_property.management_fee_plan_id or \
        #             record.id != record.estate_lease_contract_property.management_fee_plan_id.id:
        #         record.estate_lease_contract_property.write({'management_fee_plan_id': record.id})

        return record

    def write(self, vals):

        res = super().write(vals)

        # if not self.estate_lease_contract_property.management_fee_plan_id or \
        #         self.id != self.estate_lease_contract_property.management_fee_plan_id.id:
        #     self.estate_lease_contract_property.write({'management_fee_plan_id': self.id})

        return res

    def _get_one_year_days(self):
        one_year_days = self.env.user.company_id.one_year_days if self.env.user.company_id.one_year_days else 365
        return one_year_days
