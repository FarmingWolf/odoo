# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class EstateLeaseContract(models.Model):

    _name = "estate.lease.contract"
    _description = "资产租赁合同管理模型"

    name = fields.Char('合同名称', required=True, translate=True)

    contract_no = fields.Char('合同编号', required=True, translate=True)
    # contract_amount = fields.Float("合同金额", default=0.0)
    # contract_tax = fields.Float("税额", default=0.0)
    # contract_tax_per = fields.Float("税率", default=0.0)
    # contract_tax_out = fields.Float("不含税合同额", default=0.0)

    date_sign = fields.Date("合同签订日期")
    # date_start = fields.Date("合同开始日期")

    date_rent_start = fields.Date("计租开始日期")
    date_rent_end = fields.Date("计租结束日期")
    days_free = fields.Integer("免租期天数", default=0)

    days_rent_total = fields.Char(string="租赁期限", compute="_calc_days_rent_total")

    @api.depends("date_rent_start", "date_rent_end")
    def _calc_days_rent_total(self):
        for record in self:
            if record.date_rent_start and record.date_rent_end:
                date_s = fields.Date.from_string(record.date_rent_start)
                date_e = fields.Date.from_string(record.date_rent_end)
                delta = date_e - date_s
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

    tag_ids = fields.Many2many("estate.lease.contract.tag", string='合同标签')

    rent_account = fields.Many2one("estate.lease.contract.bank.account", string='租金收缴账户')
    # rent_account_name = fields.Char('租金收缴账户名', required=True, translate=True)
    # rent_account_bank = fields.Char('租金收缴账户银行', required=True, translate=True)
    # rent_account_no = fields.Char('租金收缴账号', required=True, translate=True)

    opening_date = fields.Date(string="计划开业日期")
    rental_plan_id = fields.Many2many("estate.lease.contract.rental.plan", 'contract_rental_plan_rel', 'contract_id',
                                      'rental_plan_id', string="租金方案")

    property_management_fee_plan_id = fields.Many2many("estate.lease.contract.property.management.fee.plan",
                                                       'contract_property_management_fee_plan_rel', 'contract_id',
                                                       'property_management_fee_plan_id', string="物业费方案")

    property_management_fee_account = fields.Many2one("estate.lease.contract.bank.account", string='物业费收缴账户名')
    # property_management_fee_account_name = fields.Char('物业费收缴账户名', required=True, translate=True)
    # property_management_fee_bank = fields.Char('物业费收缴账户银行', required=True, translate=True)
    # property_management_fee_account_no = fields.Char('物业费收缴账号', required=True, translate=True)

    electricity_account = fields.Many2one("estate.lease.contract.bank.account", string='电费收缴账户名')
    # electricity_account_name = fields.Char('电费收缴账户名', required=True, translate=True)
    # electricity_bank = fields.Char('电费收缴账户银行', required=True, translate=True)
    # electricity_account_no = fields.Char('电费收缴账号', required=True, translate=True)

    water_bill_account = fields.Many2one("estate.lease.contract.bank.account", string='水费收缴账户名')
    # water_bill_account_name = fields.Char('水费收缴账户名', required=True, translate=True)
    # water_bill_bank = fields.Char('水费收缴账户银行', required=True, translate=True)
    # water_bill_account_no = fields.Char('水费收缴账号', required=True, translate=True)

    parking_fee_account = fields.Many2one("estate.lease.contract.bank.account", string='停车费收缴账户名')
    pledge_account = fields.Many2one("estate.lease.contract.bank.account", string='押金收缴账户名')

    parking_space_ids = fields.Many2many('parking.space', 'contract_parking_space_rel', 'contract_id',
                                         'parking_space_id',
                                         string='停车位')

    parking_space_count = fields.Integer(default=0, string="分配停车位数量", compute="_calc_parking_space_cnt")

    @api.depends("parking_space_ids")
    def _calc_parking_space_cnt(self):
        for record in self:
            if record.parking_space_ids:
                record.parking_space_count = len(record.parking_space_ids)

    invoicing_address = fields.Char('发票邮寄地址', required=True, translate=True)
    invoicing_email = fields.Char('电子发票邮箱', required=True, translate=True)

    sales_person_id = fields.Many2one('res.users', string='招商员', index=True, default=lambda self: self.env.user)
    opt_person_id = fields.Many2one('res.users', string='录入员', index=True, default=lambda self: self.env.user)

    renter_id = fields.Many2one('res.partner', string='承租人', index=True)

    property_ids = fields.Many2many('estate.property', 'contract_property_rel', 'contract_id', 'property_id',
                                    string='租赁标的')
    rent_count = fields.Integer(default=0, string="租赁标的数量", compute="_calc_rent_total_info")
    building_area = fields.Float(default=0.0, string="总建筑面积（㎡）", compute="_calc_rent_total_info")
    rent_area = fields.Float(default=0.0, string="总计租面积（㎡）", compute="_calc_rent_total_info")

    @api.depends("property_ids")
    def _calc_rent_total_info(self):
        for record in self:
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

    contract_incentives_ids = fields.Many2one('estate.lease.contract.incentives', string='优惠方案')
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
    performance_guarantee = fields.Float(string="履约保证金（元）")
    property_management_fee_guarantee = fields.Float(string="物管费保证金（元）")

    decoration_deposit = fields.Float(string="装修押金（元）")
    decoration_management_fee = fields.Float(string="装修管理费（元）")
    decoration_water_fee = fields.Float(string="装修水费（元）")
    decoration_electricity_fee = fields.Float(string="装修电费（元）")
    refuse_collection = fields.Float(string="建筑垃圾清运费（元）")
    garbage_removal_fee = fields.Float(string="垃圾清运费（元）")

    description = fields.Text("详细信息")

    attachment_ids = fields.Many2many('ir.attachment', string="附件管理")
