# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from odoo import fields, models, api


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "报价"
    _order = "price desc"

    price = fields.Float('报价', required=True)
    status = fields.Selection(
        string='报价状态',
        selection=[('accepted', '已接受'), ('refused', '已拒绝')],
        help="点击下拉框处理报价状态",
        copy=False
    )
    partner_id = fields.Many2one('res.partner', string='报价人', index=True, required=True)
    property_id = fields.Many2one('estate.property', string='报价资产', index=True, required=True, readonly=True)
    property_type_id = fields.Many2one(related="property_id.property_type_id")

    validity = fields.Integer(default=0, string="报价有效期天数")
    date_deadline = fields.Date(compute="_compute_date_deadline", inverse="_inverse_validity", string="报价有效期至")

    _sql_constraints = [
        ('price', 'CHECK(price > 0)', '报价必须大于零')
    ]

    @api.depends("validity")
    def _compute_date_deadline(self):
        for record in self:
            print("record.create_date=[{0}]".format(record.create_date))
            if record.create_date is None or record.create_date is False:
                record.date_deadline = datetime.now().date() + timedelta(days=record.validity)
            else:
                record.date_deadline = record.create_date + timedelta(days=record.validity)

    def _inverse_validity(self):
        for record in self:
            print(record.date_deadline)
            record.validity = (record.date_deadline - record.create_date.date()).days

    active = fields.Boolean(default=True)

    def action_accept(self):
        for record in self:
            record.status = 'accepted'

    def action_refuse(self):
        for record in self:
            record.status = 'refused'

    def action_toggle_show_offer(self):
        for record in self:
            pass
