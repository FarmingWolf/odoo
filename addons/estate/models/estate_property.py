# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime
from odoo.tools.translate import _

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
    date_availability = fields.Date(copy=False, string="可租日期", compute="_compute_latest_info")
    expected_price = fields.Float(string="期望售价", default=0.0)
    selling_price = fields.Float(string="实际售价", copy=False)
    bedrooms = fields.Integer(default=0)
    building_area = fields.Float(default=0.0, string="建筑面积")
    living_area = fields.Float(default=0.0, string="使用面积")
    unit_building_area = fields.Float(default=0.0, string="套内建筑面积")
    unit_living_area = fields.Float(default=0.0, string="套内使用面积")
    share_area = fields.Float(default=0.0, string="公摊面积")
    actual_living_area = fields.Float(default=0.0, string="实际使用面积")
    rent_area = fields.Float(default=building_area, string="计租面积")
    facades = fields.Integer(default=0)
    garage = fields.Boolean(default=False)
    garden = fields.Boolean(default=False)
    garden_area = fields.Float(default=0.0)
    garden_orientation = fields.Selection(
        string='花园朝向',
        selection=[('east', '东'), ('south', '南'), ('west', '西'), ('north', '北')],
        help="点击下拉框选择花园朝向"
    )
    color = fields.Integer()

    total_area = fields.Float(compute="_compute_total_area", string="总面积（㎡）", readonly=True, copy=False)

    current_contract_id = fields.Many2one(string='当前合同', compute="_compute_latest_info",
                                          readonly=True, copy=False, store=False)

    current_contract_no = fields.Char(string='当前合同号', compute="_compute_latest_info", readonly=True, copy=False)
    current_contract_nm = fields.Char(string='当前合同名称', compute="_compute_latest_info", readonly=True, copy=False)

    latest_rent_date_e = fields.Date(string="上次出租结束日期", compute="_compute_latest_info", readonly=True, copy=False)
    latest_rent_date_s = fields.Date(string="本次出租开始日期", compute="_compute_latest_info", readonly=True, copy=False)
    out_of_rent_days = fields.Integer(string="本次空置天数", compute="_compute_latest_info", readonly=True, copy=False)

    @api.depends("current_contract_id", "date_availability")
    def _compute_latest_info(self):
        for record in self:
            # 本property对应的所有contract，原则上只能有一条active的contract
            current_contract = self.env['estate.lease.contract'].search([('property_ids', 'in', record.id),
                                                                         ('active', '=', True),
                                                                         ('state', '=', 'released')], limit=1)
            record.current_contract_id = current_contract.id if current_contract else False
            record.current_contract_no = current_contract.contract_no if current_contract else False
            record.current_contract_nm = current_contract.name if current_contract else False
            record.latest_rent_date_s = current_contract.date_rent_start if current_contract else False

            old_contract = self.env['estate.lease.contract'].search([('property_ids', 'in', record.id),
                                                                     ('active', '=', True),
                                                                     ('state', '=', 'invalid')],
                                                                    order='date_rent_end DESC',
                                                                    limit=1)
            record.latest_rent_date_e = old_contract.date_rent_end if old_contract else False
            record.date_availability = record.latest_rent_date_e + timedelta(days=1) if old_contract else False

            if record.latest_rent_date_s:
                if record.date_availability:
                    record.out_of_rent_days = (record.latest_rent_date_s - record.date_availability).days - 1
                else:
                    if record.latest_rent_date_e:
                        record.out_of_rent_days = (record.latest_rent_date_s - record.latest_rent_date_e).days - 1
                    else:
                        record.out_of_rent_days = 0
            else:
                if record.date_availability:
                    record.out_of_rent_days = (datetime.today() - record.date_availability).days
                else:
                    if record.latest_rent_date_e:
                        record.out_of_rent_days = (datetime.today() - record.latest_rent_date_e).days
                    else:
                        record.out_of_rent_days = 0

            if record.out_of_rent_days < 0:
                record.out_of_rent_days = 0

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
        selection=[('repairing', '整备中'), ('new', '新上'), ('offer_received', '收到报价'), ('offer_accepted', '接受报价'),
                   ('sold', '已租'), ('canceled', '已取消')],
        help="新上，收到报价，接受报价，已出租，已取消"
    )

    # property_offer_ids = fields.One2many('estate.property.offer', 'property_id', string="报价")
    property_offer_count = fields.Integer(compute="_compute_property_offer_count", default=0, string="报价条数")

    @api.depends("offer_ids")
    def _compute_property_offer_count(self):
        for record in self:
            print(record.offer_ids)
            record.property_offer_count = len(record.offer_ids)

    _sql_constraints = [
        ('name', 'unique(name)', '资产名称不能重复'),
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
        print("action_sold_property called")
        for record in self:
            if record.state == 'canceled':
                raise UserError(_('该记录已经被取消，不能再被设置为已售出'))

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
            if record.selling_price > 1 and float_compare(record.selling_price, record.expected_price * 0.9, 2) <= 0:
                raise ValidationError("实际售价不能低于期待售价的90%。实际售价=[{0}]；期待售价=[{1}]；期待售价的90%=[{1}*90%={2}]".
                                      format(record.selling_price, record.expected_price, record.expected_price * 0.9))

    @api.model
    def _get_state_label(self, state_value):
        """辅助方法来获取state字段的显示值"""
        # 通过字段的_get_selection方法获取这些对，然后返回对应value的label
        selection = self.env['estate.property']._fields['state'].selection
        for value, label in selection:
            if value == state_value:
                return label
        return "Unknown State[{0}]".format(state_value)

    @api.model
    def ondelete(self):
        for record in self:
            if record.state not in ("new", "canceled"):
                state_label = self._get_state_label(record.state)
                raise UserError(_('[{0}]该条资产状态为【{1}】，不可被删除!'.format(record.name, state_label)))

        return super().ondelete(self)
