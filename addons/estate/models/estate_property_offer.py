# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime
from typing import Dict, List

from odoo import fields, models, api
from odoo import _
from odoo.exceptions import ValidationError


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
            print("record.property_id.id=[{0}]".format(record.property_id.id))
            self.env['estate.property'].browse(record.property_id.id).write({'state': 'offer_accepted'})

    def action_refuse(self):
        for record in self:
            record.status = 'refused'

    # def action_toggle_show_offer(self):
    #     for record in self:
    #         pass

    # def onchange(self, values: Dict, field_names: List[str], fields_spec: Dict):
    #     return super(EstatePropertyOffer, self).onchange()

    @api.model
    def create(self, vals_list):
        # 先检查一下这条offer的价格是否高于已经接受的offer
        # property_id = self.env['estate.property.offer'].browse(vals_list['property_id'])
        property_id = vals_list.get('property_id')
        print("要对{0}添加报价".format(property_id))
        # 确保property_id已提供
        if not property_id:
            raise ValueError(_("发生错误：创建报价时，未得到资产ID"))

        # 查询同一property下的所有offer，找出最高价
        highest_offer = self.search([
            ('property_id', '=', property_id),
            ('status', '=', 'accepted'),
            ('id', '!=', False)  # 这里是为了排除当前正在创建的offer，避免自己与自己比较
        ], order='price desc', limit=1)

        # 如果找到报价且最高价高于新的offer_price，则抛出错误
        if highest_offer and vals_list.get('price', 0) <= highest_offer.price:
            raise ValidationError(_("新报价必须高于已接受的最高报价:[{0}]".format(highest_offer.price)))

        # 如果检查通过，则正常创建报价
        new_offer = super(EstatePropertyOffer, self).create(vals_list)

        # 如果可接受，那就把property设置为state=offer_received
        self.env['estate.property'].browse(vals_list['property_id']).write({'state': 'offer_received'})

        return new_offer

