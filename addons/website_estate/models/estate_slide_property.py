# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os
import random
from datetime import timedelta, datetime

from odoo.http import request
from odoo.tools.translate import _

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, babel_locale_parse
from addons.utils.models.utils import Utils

_logger = logging.getLogger(__name__)


class EstateSlideProperty(models.Model):

    _name = "estate.slide.property"
    _description = "在线招商房源"
    _inherit = 'image.mixin'

    estate_property_id = fields.Many2one("estate.property", string="在线资产", context={'bypass_company_filter': True})
    name = fields.Char('在线名称', required=True, translate=True, default=lambda self: self.estate_property_id.name)

    company_id = fields.Many2one(comodel_name='res.company', store=True, string="公司",
                                 related="estate_property_id.company_id")
    state = fields.Selection(string='资产状态', related="estate_property_id.state")
    show_ads = fields.Boolean("在线展示", default=False)
    times_viewed = fields.Integer("浏览次数", default=lambda self: random.randint(0, 300), readonly=True)
    times_liked = fields.Integer("点赞次数", default=lambda self: random.randint(0, 30), readonly=True)
    tag_ids = fields.Many2many("estate.property.tag", string="标签", related="estate_property_id.tag_ids")

    def _default_sequence(self):
        return (self.search([], order="sequence DESC", limit=1).sequence or 0) + 1

    sequence = fields.Integer(string='序号', default=_default_sequence, store=True, readonly=False)

    image_1920 = fields.Image(string="招商主图", max_width=1920, max_height=1920, compute="_get_property_main_img")
    description = fields.Text(string="主图简介", related="estate_property_id.description", readonly=True)
    sales_person_phone = fields.Char(string="联系电话",
                                     related="estate_property_id.sales_person_id.mobile_phone", readonly=True)
    sales_person_name = fields.Char(string="联系人",
                                    related="estate_property_id.sales_person_id.name", readonly=True)

    ads_img_ids = fields.One2many(comodel_name="estate.property.ads.img", related="estate_property_id.ads_img_ids")

    @api.depends('estate_property_id.ads_img_ids.sequence', 'estate_property_id.ads_img_ids.image_1920')
    def _get_property_main_img(self):
        for record in self:
            if record.estate_property_id.ads_img_ids:
                min_seq_rcd = record.estate_property_id.ads_img_ids.sorted(key=lambda r: r.sequence)[0]
                record.image_1920 = min_seq_rcd.image_1920
            else:
                record.image_1920 = False

    def action_estate_slide_property_sync(self):
        """同步在线广告房源"""
        self.env.cr.execute(f"SELECT ep.id, ep.name, ep.company_id FROM estate_property ep "
                            f"WHERE ep.active is TRUE "
                            f"  AND ep.id not in (SELECT estate_property_id FROM estate_slide_property)")
        estate_properties = self.env.cr.fetchall()
        lang = self.env.context.get('lang')

        if lang.startswith('zh_HANS'):
            lang = 'zh_CN'

        for property_id, property_name, property_company_id in estate_properties:
            new_estate_slide = [{
                'estate_property_id': property_id,
                'company_id': property_company_id,
                'name': property_name.get(lang) or property_name.get('zh_CN') or property_name.get('en_US')
            }]
            self.env['estate.slide.property'].create(new_estate_slide)

    def like_button_click(self):
        _logger.info(f"like_button_clicked")
        for record in self:
            record.times_liked += 1
