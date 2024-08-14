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
    _order = "billing_progress_info_month_from ASC"

    name = fields.Char('期间递增率名', required=True)

    # 按时间段递增的情况下：
    billing_progress_info_month_from = fields.Integer(string="从第N月起", copy=False)
    billing_progress_info_month_every = fields.Integer(string="每X个月")
    billing_progress_info_up_percentage = fields.Float(default=0.0, string="递增百分比")

    name_description = fields.Char(string="时间段递增率描述", readonly=True, compute="_combine_description")

    def _compute_sequence(self):
        for record in self:
            if record.billing_progress_info_month_from:
                record.sequence = record.billing_progress_info_month_from
            else:
                record.sequence = 1
            return record.sequence
        return 0

    sequence = fields.Integer(default=_compute_sequence, store=True, string='排序')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name',
         'unique(billing_progress_info_month_from, billing_progress_info_month_every, '
         'billing_progress_info_up_percentage, company_id)',
         '相同期间段，相同递增比例已存在')
    ]

    @api.depends("billing_progress_info_month_from", "billing_progress_info_month_every",
                 "billing_progress_info_up_percentage")
    def _combine_description(self):
        for record in self:
            record.name_description = "从第{0}个月起每{1}个月递增{2}%".format(record.billing_progress_info_month_from,
                                                                    record.billing_progress_info_month_every,
                                                                    record.billing_progress_info_up_percentage)
