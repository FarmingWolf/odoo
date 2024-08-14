# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class EstateLeaseContractIncentives(models.Model):
    _name = "estate.lease.contract.incentives"
    _description = "资产租赁合同优惠方案"

    name = fields.Char('优惠方案名称', required=True, translate=True)

    date_incentives_start = fields.Date("优惠政策开始日期")
    date_incentives_end = fields.Date("优惠政策结束日期")
    days_free = fields.Integer("免租期天数", default=0)

    business_discount_days = fields.Integer(default=0, string="经营优惠（天）")
    business_discount_amount = fields.Float(default=0.0, string="经营优惠（元）")

    decoration_discount_days = fields.Integer(default=0, string="装修优惠（天）")
    decoration_discount_amount = fields.Float(default=0.0, string="装修优惠（元）")

    support_discount_days = fields.Integer(default=0, string="扶持优惠（天）")
    support_discount_amount = fields.Float(default=0.0, string="扶持优惠（元）")

    special_discount_days = fields.Integer(default=0, string="专项优惠（天）")
    special_discount_amount = fields.Float(default=0.0, string="专项优惠（元）")

    incentives_days_total = fields.Integer(string="总优惠天数", readonly=True, compute="_compute_incentives_total")
    incentives_amount_total = fields.Integer(string="总优惠金额（元）", readonly=True, compute="_compute_incentives_total")

    name_description = fields.Text("详细信息")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends("days_free", "business_discount_days", "business_discount_amount", "decoration_discount_days",
                 "decoration_discount_amount",
                 "support_discount_days", "support_discount_amount", "special_discount_days", "special_discount_amount")
    def _compute_incentives_total(self):
        for record in self:
            record.incentives_days_total = record.days_free + record.business_discount_days + \
                                           record.decoration_discount_days + record.support_discount_days + \
                                           record.special_discount_days

            record.incentives_amount_total = record.business_discount_amount + record.decoration_discount_amount + \
                                             record.support_discount_amount + record.special_discount_amount

