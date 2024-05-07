# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstatePropertyType(models.Model):

    _name = "estate.property.type"
    _description = "资产类型模型"
    _order = "sequence"

    name = fields.Char('资产类型', required=True)
    property_ids = fields.One2many('estate.property', 'property_type_id', string="资产条目")
    sequence = fields.Integer('Sequence', default=1, help="按类型排序")

    offer_ids = fields.One2many('estate.property.offer', 'property_type_id', string="报价")
    offer_count = fields.Integer(compute="_compute_offer_count", default=0)

    @api.depends("offer_ids")
    def _compute_offer_count(self):
        for record in self:
            print(record.offer_ids)
            record.offer_count = len(record.offer_ids)

    active = fields.Boolean(default=True)
    _sql_constraints = [
        ('name', 'unique(name)', '资产类型不能重复')
    ]

    def action_toggle_show_offer(self):
        for record in self:
            pass
