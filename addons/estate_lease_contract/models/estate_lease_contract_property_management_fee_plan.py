# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractPropertyManagementFeePlan(models.Model):
    _name = "estate.lease.contract.property.management.fee.plan"
    _description = "资产租赁合同物业费方案"
    _order = "sequence"

    name = fields.Char('物业费方案', required=True)
    sequence = fields.Integer('排序', default=1)
    property_management_fee_price = fields.Float(default=0.0, string="单价（元/月/㎡）")
    billing_progress_method_id = fields.Selection(string='递进方式',
                                                  selection=[('by_period', '按时间段递增'), ('no_progress', '不递增')],
                                                  )
    # 按时间段递增的情况下：
    billing_progress_info_month_from = fields.Integer(string="从第N月起")
    billing_progress_info_month_every = fields.Integer(string="每X个月")
    billing_progress_info_up_percentage = fields.Float(default=0.0, string="递增百分比")
    name_description = fields.Char(string="方案描述", compute="_get_name_description")

    @api.depends("name", "property_management_fee_price", "billing_progress_method_id",
                 "billing_progress_info_month_from", "billing_progress_info_month_every",
                 "billing_progress_info_up_percentage")
    def _get_name_description(self):
        if self:
            for record in self:
                if record:
                    if record.billing_progress_method_id == "no_progress":
                        record.name_description = "{0}：物业费单价{1}元/月/㎡，不递增。".format(record.name,
                                                                                  record.property_management_fee_price)
                    else:
                        record.name_description = "{0}：物业费单价{1}元/月/㎡，从第{2}个月起，每{3}个月递增{4}%。". \
                            format(record.name,
                                   record.property_management_fee_price,
                                   record.billing_progress_info_month_from,
                                   record.billing_progress_info_month_every,
                                   record.billing_progress_info_up_percentage)

    _sql_constraints = [
        ('name', 'unique(name)', '物业费方案名不能重复')
    ]
