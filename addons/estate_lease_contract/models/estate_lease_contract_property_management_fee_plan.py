# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractPropertyManagementFeePlan(models.Model):

    _name = "estate.lease.contract.property.management.fee.plan"
    _description = "资产租赁合同物业费方案"
    _order = "sequence"

    name = fields.Char('资产租赁合同物业费方案', required=True)
    sequence = fields.Integer('排序', default=1)
    property_management_fee_price = fields.Float(default=0.0, string="物业费单价（元/月/㎡）")
    billing_progress_method_id = fields.Selection(string='递进方式',
                                                  selection=[('by_period', '按时间段'), ('by_turnover', '按营业额')],
                                                  )
    # 按时间段递增的情况下：
    billing_progress_info_month_from = fields.Integer(string="从第N月起")
    billing_progress_info_month_every = fields.Integer(string="每X个月")
    billing_progress_info_up_percentage = fields.Float(default=0.0, string="递增百分比")

    _sql_constraints = [
        ('name', 'unique(name)', '物业费方案名不能重复')
    ]
