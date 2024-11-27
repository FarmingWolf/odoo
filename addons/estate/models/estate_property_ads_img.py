# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class EstatePropertyAdsImg(models.Model):
    _name = "estate.property.ads.img"
    _description = "资产在线招商用图"
    _order = "sequence"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    property_id = fields.Many2one('estate.property', string="招商标的", ondelete="cascade", readonly=True, store=True,
                                  default=lambda self: self._get_context_property_id(), required=True,
                                  compute="_compute_property_id")

    def _default_sequence(self):
        if not self.property_id:
            return 0

        return (self.search([('property_id', '=', self.property_id)], order="sequence DESC", limit=1).sequence or 0) + 1

    sequence = fields.Integer(string='序号', default=_default_sequence, store=True, readonly=False, required=True,
                              help="第一张图用于广告看板主图，其他用于在线浏览")

    def _get_context_property_id(self):
        if "PROPERTY_ID" in self.env.context:
            self.property_id = self.env.context["PROPERTY_ID"]
            return self.env.context["PROPERTY_ID"]

    def _compute_property_id(self):
        for record in self:
            if "PROPERTY_ID" in self.env.context:
                record.property_id = self.env.context["PROPERTY_ID"]
            else:
                record.property_id = record.property_id

    image_1920 = fields.Image(string="在线招商图", max_width=1920, max_height=1920)

    company_id = fields.Many2one(comodel_name='res.company', store=True, related="property_id.company_id")

    @api.model
    def default_get(self, in_fields):
        res = super().default_get(in_fields)
        if 'property_id' in in_fields and self._context.get('PROPERTY_ID'):
            _logger.info(f"self._context.get-PROPERTY_ID={self._context.get('PROPERTY_ID')}")
            res.update({
                'property_id': self._context.get('PROPERTY_ID')
            })
        return res
