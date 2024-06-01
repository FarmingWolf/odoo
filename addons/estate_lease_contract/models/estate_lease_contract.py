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
    contract_amount = fields.Float("合同金额", default=0.0)
    contract_tax = fields.Float("税额", default=0.0)
    contract_tax_per = fields.Float("税率", default=0.0)
    contract_tax_out = fields.Float("不含税合同额", default=0.0)

    date_sign = fields.Date("合同签订日期")
    date_start = fields.Date("合同开始日期")
    date_end = fields.Date("合同结束日期")

    date_rent_start = fields.Date("合同计租日期")
    days_free = fields.Integer("免租期天数", default=0)
    date_deliver = fields.Date("计划交付日期")
    date_decorate_start = fields.Date("计划装修开始日期")
    date_decorate_end = fields.Date("计划装修结束日期")

    contract_type_id = fields.Many2one("estate.lease.contract.type", string="合同类型")
    tag_ids = fields.Many2many("estate.lease.contract.tag", string='合同标签')

    rent_account = fields.Many2one("estate.lease.contract.bank.account", string='租金收缴账户')
    # rent_account_name = fields.Char('租金收缴账户名', required=True, translate=True)
    # rent_account_bank = fields.Char('租金收缴账户银行', required=True, translate=True)
    # rent_account_no = fields.Char('租金收缴账号', required=True, translate=True)

    rental_plan_id = fields.Many2one("estate.lease.contract.rental.plan", string="租金方案")

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

    parking_space_ids = fields.Many2many('parking.space', 'contract_parking_space_rel', 'contract_id',
                                         'parking_space_id',
                                         string='停车位')

    invoicing_address = fields.Char('发票邮寄地址', required=True, translate=True)
    invoicing_email = fields.Char('电子发票邮箱', required=True, translate=True)

    sales_person_id = fields.Many2one('res.users', string='招商员', index=True, default=lambda self: self.env.user)
    opt_person_id = fields.Many2one('res.users', string='录入员', index=True, default=lambda self: self.env.user)

    renter_id = fields.Many2one('res.partner', string='承租人', index=True)
    contact_id = fields.Many2one('res.partner', string='联系人', index=True)

    property_ids = fields.Many2many('estate.property', 'contract_property_rel', 'contract_id', 'property_id',
                                    string='租赁场地')

    description = fields.Text("详细信息")

