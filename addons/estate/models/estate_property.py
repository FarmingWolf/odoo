# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime
from importlib.resources import _

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class EstateProperty(models.Model):
    # def onchange(self, values: Dict, field_names: List[str], fields_spec: Dict):
    #     pass

    _name = "estate.property"
    _description = "资产模型"

    name = fields.Char('资产名称', required=True, translate=True)
    property_type_id = fields.Many2one("estate.property.type", string="资产类型")
    tag_ids = fields.Many2many("estate.property.tag")
    sales_person_id = fields.Many2one('res.users', string='销售员', index=True,
                                      default=lambda self: self.env.user)
    buyer_id = fields.Many2one('res.partner', string='购买人', index=True)
    offer_ids = fields.One2many('estate.property.offer', 'property_id', string="报价")
    floor = fields.Integer(default=1, string='楼层')
    description = fields.Text("详细信息")
    postcode = fields.Char()
    three_months_later = datetime.today() + timedelta(days=90)
    date_availability = fields.Date(default=three_months_later, copy=False)
    expected_price = fields.Float("期望售价", default=0.0)
    selling_price = fields.Float("实际售价", copy=False)
    bedrooms = fields.Integer(default=0)
    living_area = fields.Float(default=0.0)
    facades = fields.Integer(default=0)
    garage = fields.Boolean(default=False)
    garden = fields.Boolean(default=False)
    garden_area = fields.Float(default=0.0)
    garden_orientation = fields.Selection(
        string='花园朝向',
        selection=[('east', '东'), ('south', '南'), ('west', '西'), ('north', '北')],
        help="点击下拉框选择花园朝向"
    )
    total_area = fields.Float(compute="_compute_total_area", string="总面积（㎡）", readonly=True)

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    best_price = fields.Float(compute="_get_best_price", string="最高报价", readonly=True)

    @api.depends("offer_ids.price")
    def _get_best_price(self):
        for record in self:
            accepted_prices = record.offer_ids.filtered(lambda offer: offer.status == 'accepted')
            _best_price = accepted_prices.mapped('price')
            record.best_price = max(_best_price) if _best_price else 0.0

    active = fields.Boolean(default=True)
    state = fields.Selection(
        string='资产状态',
        selection=[('new', '新上'), ('offer_received', '收到报价'), ('offer_accepted', '接受报价'),
                   ('sold', '已售出'), ('canceled', '已取消')],
        help="新上，收到报价，接受报价，已售出，已取消"
    )

    property_offer_ids = fields.One2many('estate.property.offer', 'property_id', string="报价")
    property_offer_count = fields.Integer(compute="_compute_property_offer_count", default=0, string="报价条数")

    @api.depends("property_offer_ids")
    def _compute_property_offer_count(self):
        for record in self:
            print(record.property_offer_ids)
            record.property_offer_count = len(record.property_offer_ids)

    active = fields.Boolean(default=True)
    _sql_constraints = [
        ('name', 'unique(name)', '资产类型不能重复')
    ]

    _sql_constraints = [
        ('expected_price', 'CHECK(expected_price > 0)', '期待售价必须大于零'),
        ('selling_price', 'CHECK(selling_price > 0)', '实际售价必须大于零'),
    ]

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 100
            self.garden_orientation = 'south'
        else:
            self.garden_area = 0
            self.garden_orientation = ''

    # 取消该条记录
    def action_cancel_property(self):
        for record in self:
            record.state = 'canceled'

    def action_sold_property(self):
        for record in self:
            if record.state == 'canceled':
                raise UserError(_('该记录已经被取消，不能再被设置为已售出'))
                print("设置错误之后")

            # 设置实际售价和购买者
            record.selling_price = record.best_price

            accepted_prices = record.offer_ids.filtered(lambda offer: offer.status == 'accepted')
            for rcd in accepted_prices:
                print("partner_id=[{0}],price=[{1}]".format(rcd.partner_id, rcd.price))
            _best_price_rcd = accepted_prices.sorted(key=lambda r: r.price, reverse=True)

            for rcd in _best_price_rcd:
                print("after search partner_id=[{0}],price=[{1}]".format(rcd.partner_id, rcd.price))

            # 如果设置售出，那么一定已经有报价了
            record.buyer_id = _best_price_rcd[0].partner_id

            if record.state != 'sold':
                record.state = 'sold'

    @api.constrains('selling_price')
    def _check_selling_price(self):
        for record in self:
            if float_compare(record.selling_price, record.expected_price * 0.9, 2) <= 0:
                raise ValidationError("实际售价不能低于期待售价的90%。实际售价=[{0}]；期待售价=[{1}]；期待售价的90%=[{1}*90%={2}]".
                                      format(record.selling_price, record.expected_price, record.expected_price * 0.9))
