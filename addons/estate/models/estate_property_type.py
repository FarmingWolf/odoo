# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstatePropertyType(models.Model):

    _name = "estate.property.type"
    _description = "资产类型模型"
    _order = "sequence"

    name = fields.Char('资产类型', required=True)
    property_ids = fields.One2many('estate.property', 'property_type_id', string="资产条目")
    property_count = fields.Integer(compute="_compute_property_count", default=0)
    sequence = fields.Integer('Sequence', default=1, help="排序")

    offer_ids = fields.One2many('estate.property.offer', 'property_type_id', string="报价")
    offer_count = fields.Integer(compute="_compute_offer_count", default=0)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends("property_ids")
    def _compute_property_count(self):
        for record in self:
            record.property_count = len(record.property_ids)

    @api.depends("offer_ids")
    def _compute_offer_count(self):
        for record in self:
            print(record.offer_ids)
            record.offer_count = len(record.offer_ids)

    active = fields.Boolean(default=True)
    _sql_constraints = [
        ('name', 'unique(name, company_id)', '资产类型不能重复')
    ]

    def action_toggle_show_offer(self):
        for record in self:
            pass

    def _get_chinese_name(self):
        return "报价条数"
