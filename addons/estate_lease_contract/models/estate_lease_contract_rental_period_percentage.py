# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractRentalPeriodPercentage(models.Model):

    """
    第13个月起每12个月递增2.5%
    第25个月起每12个月递增4%
    第25个月起每12个月递增5%
    第13个月起每12个月递增0%
    第49个月起每48个月递增12.2%
    第37个月起每24个月递增0%
    第13个月起每12个月递增5.19%
    第49个月起每12个月递增18.52%
    第25个月起每24个月递增7%
    第13个月起每12个月递增25%
    第37个月起每36个月递增6.35%
    第3个月起每12个月递增357.25%
    ……其他可自定义
    """
    _name = "estate.lease.contract.rental.period.percentage"
    _description = "递增率设置"
    _order = "sequence"

    name = fields.Char('期间递增率名', required=True)
    sequence = fields.Integer('排序', default=1)
    # 按时间段递增的情况下：
    billing_progress_info_month_from = fields.Integer(string="从第N月起")
    billing_progress_info_month_every = fields.Integer(string="每X个月")
    billing_progress_info_up_percentage = fields.Float(default=0.0, string="递增百分比")

    name_description = fields.Char(string="时间段递增率描述", readonly=True, compute="_combine_description")

    _sql_constraints = [
        ('name',
         'unique(billing_progress_info_month_from, billing_progress_info_month_every, '
         'billing_progress_info_up_percentage)',
         '相同期间段，相同递增比例已存在')
    ]

    @api.depends("billing_progress_info_month_from", "billing_progress_info_month_every",
                 "billing_progress_info_up_percentage")
    def _combine_description(self):
        for record in self:
            record.name_description = "从第{0}个月起每{1}个月递增{2}%".format(record.billing_progress_info_month_from,
                                                                    record.billing_progress_info_month_every,
                                                                    record.billing_progress_info_up_percentage)
