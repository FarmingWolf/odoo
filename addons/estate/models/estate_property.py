# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os
from datetime import timedelta, datetime

from odoo.http import request
from odoo.tools.translate import _

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from addons.utils.models.utils import Utils

_logger = logging.getLogger(__name__)


def _check_current_contract_valid(record):
    if record.current_contract_id:
        if record.latest_rent_date_s and record.latest_rent_date_e:
            if fields.Date.context_today(record) >= record.latest_rent_date_s and fields.Date.context_today(
                    record) <= record.latest_rent_date_e:
                record.state = "sold"
                return True

            if fields.Date.context_today(record) <= record.latest_rent_date_s:
                record.state = "offer_accepted"

            if record.state == "sold" and fields.Date.context_today(record) > record.latest_rent_date_e:
                record.state = "canceled"

    return False


def _get_payment_method_str(record):
    if record.rent_plan_id:
        deposit_months = record.deposit_months if record.deposit_months else 0
        if record.rent_plan_id.payment_period:
            return f"押{'{:.2f}'.format(round(deposit_months, 2)).rstrip('0').rstrip('.')}" \
                   f"付{record.rent_plan_id.payment_period}"
    else:
        return ""


def _get_property_cnt_limit():
    module_path = os.path.dirname(os.path.abspath(__file__))
    _logger.info(f"module_path={module_path}")
    tgt_path = os.path.join(module_path, '..\\..\\..\\', 'estate_management.zip')
    pwd_base = "491491491Tech+"
    # 先获取客户名缩写
    args = {
        "file_2_customer": tgt_path,
        "customer_name_4_pwd_fn": "c_info_5_ck",
        "zip_pwd": pwd_base,
    }
    custom_name_short = Utils.get_customer_name_short(args)
    _logger.info(f"custom_name_short={custom_name_short}")

    args = {
        "file_2_customer": tgt_path,
        "tiered_pricing_info_fn": "c_info_4_ck",
        "zip_pwd": pwd_base + custom_name_short,
    }
    property_limit = Utils.get_property_cnt_limit(args)
    _logger.info(f"property_limit={property_limit}")

    return property_limit


class EstateProperty(models.Model):
    # def onchange(self, values: Dict, field_names: List[str], fields_spec: Dict):
    #     pass

    _name = "estate.property"
    _description = "资产模型"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('资产名称', required=True, translate=True, tracking=True)
    property_type_id = fields.Many2one("estate.property.type", string="资产类型",
                                       default=lambda self: self._get_default_property_type())
    tag_ids = fields.Many2many("estate.property.tag", string="标签")
    sales_person_id = fields.Many2one('res.users', string='销售员', index=True,
                                      default=lambda self: self.env.user,
                                      domain="[('company_id', '=', company_id)]")
    buyer_id = fields.Many2one('res.partner', string='购买人', index=True, tracking=True,
                               domain="[('company_id', '=', company_id)]")
    offer_ids = fields.One2many('estate.property.offer', 'property_id', string="报价", tracking=True)
    building_no = fields.Char(string='楼号', group_expand='_read_group_building_nos')
    floor = fields.Char(default=1, string='楼层')
    room_no = fields.Char(string='房间号')
    description = fields.Text("详细信息")
    postcode = fields.Char()
    date_availability = fields.Date(copy=False, string="可租日期", tracking=True)
    expected_price = fields.Float(string="期望价格（元/天/㎡）", default=0.0, tracking=True)
    announced_price = fields.Float(string="报价（元/天/㎡）", default=0.0, tracking=True)
    selling_price = fields.Float(string="实际价格（元/天/㎡）", copy=False, default=0.0, tracking=True)
    bedrooms = fields.Integer(default=0)
    building_area = fields.Float(default=0.0, string="总建筑面积（㎡）", help="实用面积+花园面积", tracking=True)
    living_area = fields.Float(default=0.0, string="使用面积（㎡）", tracking=True)
    unit_building_area = fields.Float(default=0.0, string="套内建筑面积（㎡）", tracking=True)
    unit_living_area = fields.Float(default=0.0, string="套内使用面积（㎡）", tracking=True)
    share_area = fields.Float(default=0.0, string="公摊面积（㎡）", tracking=True)
    actual_living_area = fields.Float(default=0.0, string="实际使用面积（㎡）", tracking=True)
    rent_area = fields.Float(default=100, string="计租面积（㎡）", help="租赁合同用面积", tracking=True)
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

    def _default_sequence(self):
        return (self.search([], order="sequence", limit=1).sequence or 0) + 1

    sequence = fields.Integer(string='序号', default=_default_sequence, help="可在列表页面拖拽排序",
                              compute="_compute_sequence", store=True, readonly=False)
    order_by_name = fields.Boolean(string="以名称排序", default=True, help="勾选则以名称为排序基准，不勾选则以序号为排序基准")
    total_area = fields.Float(compute="_compute_total_area", string="总使用面积（㎡）", readonly=True, copy=False)

    current_contract_id = fields.Char(string='当前合同', compute="_compute_latest_info", readonly=True, copy=False,
                                      store=False)

    current_contract_no = fields.Char(string='当前合同号', compute="_compute_latest_info", readonly=True, copy=False)
    current_contract_nm = fields.Char(string='当前合同名称', compute="_compute_latest_info", readonly=True, copy=False)

    last_rent_date_s = fields.Date(string="上次出租开始日期", compute="_compute_latest_info", readonly=True, copy=False)
    last_rent_date_e = fields.Date(string="上次出租结束日期", compute="_compute_latest_info", readonly=True, copy=False)
    latest_rent_date_s = fields.Date(string="本次出租开始日期", compute="_compute_latest_info", readonly=True, copy=False)
    latest_rent_date_e = fields.Date(string="本次出租结束日期", compute="_compute_latest_info", readonly=True, copy=False)
    out_of_rent_days = fields.Integer(string="本次空置天数", compute="_compute_latest_info", readonly=True, copy=False)
    latest_sign_date = fields.Date(string="合同签订日期", compute="_compute_latest_info", readonly=True, copy=False)
    latest_contract_date_s = fields.Date(string="合同开始日期", compute="_compute_latest_info", readonly=True, copy=False)
    latest_rent_days = fields.Char(string="租赁期限", compute="_compute_latest_info", readonly=True, copy=False)
    latest_payment_method = fields.Char(string="付款方式", compute="_compute_latest_info", readonly=True, copy=False)
    latest_deposit = fields.Float(string="押金", compute="_compute_latest_info", readonly=True, copy=False)
    latest_monthly_rent = fields.Float(string="月租金（元）", compute="_compute_latest_info", readonly=True, copy=False)
    latest_annual_rent = fields.Float(string="年租金（元）", compute="_compute_latest_info", readonly=True, copy=False)
    latest_is_renew = fields.Boolean(string="是否续租", copy=False)
    latest_contact_person = fields.Char(string="承租人", compute="_compute_latest_info", readonly=True, copy=False)
    latest_contact_person_tel = fields.Char(string="联系电话", compute="_compute_latest_info", readonly=True, copy=False)
    latest_free_days = fields.Date(string="免租期", copy=False)
    more_info_invisible = fields.Boolean(string="更多信息", copy=False, default=False, store=False)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    latitude = fields.Float(string="latitude")
    longitude = fields.Float(string="longitude")

    def _get_default_property_type(self):
        default_types = self.env["estate.property.type"].search([('name', 'ilike', '办公')], limit=1)
        tgt_type_id = False
        for default_type in default_types:
            tgt_type_id = default_type.id

        return tgt_type_id

    @api.model
    def update_property_location(self, record_id, latitude, longitude):
        """
        更新模型的经纬度信息
        :param record_id: 当前记录的ID
        :param latitude: 纬度
        :param longitude: 经度
        :return: True
        """
        record = self.browse(record_id)
        if record:
            record.write({
                'latitude': latitude,
                'longitude': longitude,
            })
            return True
        return False

    @api.depends("name", 'order_by_name')
    def _compute_sequence(self):
        for record in self:

            record.sequence = record.sequence

            all_rcds = self.env['estate.property'].search([('company_id', '=', self.company_id.id)], order="name ASC")
            i = 0
            for rcd in all_rcds:
                if rcd.order_by_name and rcd.sequence != i:
                    _logger.info(f"重新排序property rcd{rcd.id}.sequence={rcd.sequence}→{i}")
                    rcd.sequence = i
                i += 1

    @api.depends("_id")
    def _get_context(self):
        _logger.info(f"资产模型：default_contract_id=【{request.session.get('session_contract_id')}】")
        _logger.info(f"资产模型：contract_read_only=【{request.session.get('contract_read_only')}】")

    # @api.onchange("building_area")
    # def _get_building_area(self):
    #     for record in self:
    #         if record.rent_area == 0 and record.building_area != 0:
    #             record.rent_area = record.building_area

    @api.depends("current_contract_id", "date_availability")
    def _compute_latest_info(self):
        for record in self:
            # 本property对应的所有contract，原则上只能有一条active的contract
            _logger.info("资产管理原始模型")
            current_contract = self.env['estate.lease.contract'].search([('property_ids', 'in', record.id),
                                                                         ('active', '=', True),
                                                                         ('state', '=', 'released')],
                                                                        order='date_rent_end DESC', limit=1)
            if current_contract:
                if record.current_contract_id != current_contract.id:
                    record.current_contract_id = current_contract.id
                if record.current_contract_no != current_contract.contract_no:
                    record.current_contract_no = current_contract.contract_no
                if record.current_contract_nm != current_contract.name:
                    record.current_contract_nm = current_contract.name
                if record.latest_rent_date_s != current_contract.date_rent_start:
                    record.latest_rent_date_s = current_contract.date_rent_start
                if record.latest_rent_date_e != current_contract.date_rent_end:
                    record.latest_rent_date_e = current_contract.date_rent_end
                if record.latest_sign_date != current_contract.date_sign:
                    record.latest_sign_date = current_contract.date_sign
                if record.latest_contract_date_s != current_contract.date_start:
                    record.latest_contract_date_s = current_contract.date_start
                if record.latest_rent_days != current_contract.days_rent_total:
                    record.latest_rent_days = current_contract.days_rent_total
                if record.latest_contact_person != current_contract.renter_id.name:
                    record.latest_contact_person = current_contract.renter_id.name
                if record.latest_contact_person_tel != current_contract.renter_id.phone:
                    record.latest_contact_person_tel = current_contract.renter_id.phone
            else:
                if record.current_contract_id:
                    record.current_contract_id = False
                if record.current_contract_no:
                    record.current_contract_no = False
                if record.current_contract_nm:
                    record.current_contract_nm = False
                if record.latest_rent_date_s:
                    record.latest_rent_date_s = False
                if record.latest_rent_date_e:
                    record.latest_rent_date_e = False
                if record.latest_sign_date:
                    record.latest_sign_date = False
                if record.latest_contract_date_s:
                    record.latest_contract_date_s = False
                if record.latest_rent_days:
                    record.latest_rent_days = False
                if record.latest_contact_person:
                    record.latest_contact_person = False
                if record.latest_contact_person_tel:
                    record.latest_contact_person_tel = False

            tmp_str = _get_payment_method_str(record)
            if record.latest_payment_method != tmp_str:
                record.latest_payment_method = tmp_str
            if record.latest_deposit != record.deposit_amount:
                record.latest_deposit = record.deposit_amount
            if record.rent_amount_monthly_adjust:
                if record.latest_monthly_rent != record.rent_amount_monthly_adjust:
                    record.latest_monthly_rent = record.rent_amount_monthly_adjust
            else:
                if record.latest_monthly_rent != record.rent_amount_monthly_auto:
                    record.latest_monthly_rent = record.rent_amount_monthly_auto
            if record.latest_annual_rent != record.latest_monthly_rent * 12:
                record.latest_annual_rent = record.latest_monthly_rent * 12

            old_contract = self.env['estate.lease.contract'].search([('property_ids', 'in', record.id),
                                                                     ('active', '=', True),
                                                                     ('state', '=', 'invalid')],
                                                                    order='date_rent_end DESC',
                                                                    limit=1)

            if old_contract:
                if record.last_rent_date_s != old_contract.date_rent_start:
                    record.last_rent_date_s = old_contract.date_rent_start

                if old_contract.terminated and old_contract.date_terminated:
                    if record.last_rent_date_e != old_contract.date_terminated:
                        record.last_rent_date_e = old_contract.date_terminated
                else:
                    if record.last_rent_date_e != old_contract.date_rent_end:
                        record.last_rent_date_e = old_contract.date_rent_end

                if record.date_availability != record.last_rent_date_e + timedelta(days=1):
                    record.date_availability = record.last_rent_date_e + timedelta(days=1)
            else:
                if record.last_rent_date_s:
                    record.last_rent_date_s = False
                if record.last_rent_date_e:
                    record.last_rent_date_e = False

            if record.latest_rent_date_s:
                if record.date_availability:
                    if record.out_of_rent_days != (record.latest_rent_date_s - record.date_availability).days - 1:
                        record.out_of_rent_days = (record.latest_rent_date_s - record.date_availability).days - 1
                else:
                    if record.last_rent_date_e:
                        if record.out_of_rent_days != (record.latest_rent_date_s - record.last_rent_date_e).days - 1:
                            record.out_of_rent_days = (record.latest_rent_date_s - record.last_rent_date_e).days - 1
                    else:
                        if record.out_of_rent_days:
                            record.out_of_rent_days = 0
            else:
                if record.date_availability:
                    if record.out_of_rent_days != (fields.Date.context_today(self) - record.date_availability).days:
                        record.out_of_rent_days = (fields.Date.context_today(self) - record.date_availability).days
                else:
                    if record.last_rent_date_e:
                        if record.out_of_rent_days != (fields.Date.context_today(self) - record.last_rent_date_e).days:
                            record.out_of_rent_days = (fields.Date.context_today(self) - record.last_rent_date_e).days
                    else:
                        if record.out_of_rent_days:
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
        string='资产状态', default='new',
        selection=[('repairing', '整备中'), ('new', '待租中'), ('offer_received', '洽谈中'), ('offer_accepted', '接受报价'),
                   ('sold', '已租'), ('canceled', '已取消'), ('out_dated', '租约已到期')],
    )
    state_color = fields.Integer(string='租控图颜色', compute='_compute_state_color')

    @api.model
    def _read_group_building_nos(self, stages, domain, order):
        # 获取当前模型的所有记录的building_no字段值，去除重复并排序
        records = self.search([('company_id', '=', self.env.user.company_id.id)])
        building_nos = [' ' if not r.building_no or not r.building_no.strip() else r.building_no for r in records]

        # 去重并排序
        unique_sorted_building_nos = sorted(set(building_nos))

        # 创建一个字典来存储每个building_no的折叠状态
        fold_state = {bno: bno == ' ' for bno in unique_sorted_building_nos}

        # 返回两个元素：第一个是分组依据的列表，第二个是折叠状态的字典
        return fold_state

    @api.depends('state')
    def _compute_state_color(self):
        for record in self:
            # 查找当前用户对当前状态的配置
            config = self.env['estate.property.state.color'].search([
                ('company_id', '=', self.company_id.id),
                ('state', '=', record.state),
            ], limit=1)
            # 如果找到配置，使用配置的颜色；否则使用默认颜色（0表示无颜色）
            record.state_color = config.color if config else 0

    # property_offer_ids = fields.One2many('estate.property.offer', 'property_id', string="报价")
    property_offer_count = fields.Integer(compute="_compute_property_offer_count", default=0, string="报价条数")

    ads_img_ids = fields.One2many(comodel_name="estate.property.ads.img", inverse_name="property_id")

    @api.depends("offer_ids")
    def _compute_property_offer_count(self):
        for record in self:
            print(record.offer_ids)
            record.property_offer_count = len(record.offer_ids)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '资产名称不能重复'),
        ('expected_price', 'CHECK(expected_price >= 0)', '期待售价必须大于零'),
        ('selling_price', 'CHECK(selling_price >= 0)', '实际售价不能小于零'),
    ]

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 100
            self.garden_orientation = 'south'
        else:
            self.garden_area = 0
            self.garden_orientation = ''

    def action_change_state_repairing(self):
        for record in self:
            if _check_current_contract_valid(record):
                raise ValidationError(_("当前资产已在租，不能更改资产状态。"))

            record.state = 'repairing'

    def action_change_state_new(self):
        for record in self:
            if _check_current_contract_valid(record):
                raise ValidationError(_("当前资产已在租，不能更改资产状态。"))

            record.state = 'new'

    def action_change_state_offer_received(self):
        for record in self:
            if _check_current_contract_valid(record):
                raise ValidationError(_("当前资产已在租，不能更改资产状态。"))

            record.state = 'offer_received'

            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': "恭喜你！资产进入洽谈中！祝早日签约租赁合同！",
                    'img_url': f'/web/image?model=res.users&field=avatar_128&id={self.env.user.id}'
                               if self.env.user.image_1024 else '/web/static/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }

    def action_change_state_offer_accepted(self):
        for record in self:
            if _check_current_contract_valid(record):
                raise ValidationError(_("当前资产已在租，不能更改资产状态。"))

            record.state = 'offer_accepted'

            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': "恭喜你！资产已接受报价！租赁业务蒸蒸日上！",
                    'img_url': f'/web/image?model=res.users&field=avatar_128&id={self.env.user.id}'
                               if self.env.user.image_1024 else '/web/static/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }

    # 取消该条记录
    def action_cancel_property(self):
        for record in self:
            if _check_current_contract_valid(record):
                raise ValidationError(_("当前资产已在租，不能更改资产状态。"))
            record.state = 'canceled'

    def action_property_out_dated(self):
        for record in self:
            if _check_current_contract_valid(record):
                raise ValidationError(_("当前资产已在租，不能更改资产状态。"))
            record.state = 'out_dated'

    def action_sold_property(self):
        for record in self:
            if not _check_current_contract_valid(record):
                raise ValidationError(_('当前资产没有生效的租赁合同，不能被设置为已租。请前往合同管理模块，在合同中选择资产。'))

            # 设置实际售价和购买者
            record.selling_price = record.best_price

            accepted_prices = record.offer_ids.filtered(lambda offer: offer.status == 'accepted')
            for rcd in accepted_prices:
                print("partner_id=[{0}],price=[{1}]".format(rcd.partner_id, rcd.price))
            _best_price_rcd = accepted_prices.sorted(key=lambda r: r.price, reverse=True)

            for rcd in _best_price_rcd:
                print("after search partner_id=[{0}],price=[{1}]".format(rcd.partner_id, rcd.price))

            # 如果设置售出，那么一定已经有报价了
            if not _best_price_rcd:
                raise ValidationError(_("这是个保留功能，请不要在这里设置已售出。请前往合同管理模块，在合同中选择资产。"))

            record.buyer_id = _best_price_rcd[0].partner_id

            if record.state != 'sold':
                record.state = 'sold'

    @api.constrains('date_availability')
    def _check_date_availability(self):
        for record in self:
            if record.date_availability and record.last_rent_date_e:
                if record.date_availability <= record.last_rent_date_e:
                    raise ValidationError("可租日期不能早于上次出租结束日期")

    @api.model
    def _get_state_label(self, state_value):
        """辅助方法来获取state字段的显示值"""
        # 通过字段的_get_selection方法获取这些对，然后返回对应value的label
        selection = self.env['estate.property']._fields['state'].selection
        for value, label in selection:
            if value == state_value:
                return label
        return "Unknown State[{0}]".format(state_value)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_new_canceled(self):
        for record in self:
            if record.state not in ("new", "canceled"):
                state_label = self._get_state_label(record.state)
                raise UserError(_('[{0}]该条资产状态为【{1}】，不可被删除!'.format(record.name, state_label)))

        # return super().unlink()

    @api.model
    def create(self, vals):
        # 资产条目数限制
        property_limit = _get_property_cnt_limit()
        properties_cnt = self.env['estate.property'].search_count([])
        _logger.info(f"property_limit={property_limit};已存在properties_cnt={properties_cnt}")
        if properties_cnt and properties_cnt + 1 > property_limit:
            raise UserError(f'当前版本最多支持{property_limit}条资产条目')

        ret = super().create(vals)
        return ret

    @api.model_create_multi
    def create(self, vals_list):
        property_limit = _get_property_cnt_limit()
        properties_cnt = self.env['estate.property'].search_count([])
        _logger.info(f"property_limit={property_limit};已存在properties_cnt={properties_cnt};准备插入{len(vals_list)}条")
        if properties_cnt and properties_cnt + len(vals_list) > property_limit:
            raise UserError(f'当前版本最多支持{property_limit}条资产条目')

        ret = super().create(vals_list)
        return ret
