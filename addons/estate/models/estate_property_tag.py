# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstatePropertyTag(models.Model):

    _name = "estate.property.tag"
    _description = "资产标签"

    name = fields.Char('资产标签', required=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name', 'unique(name)', '资产标签不能重复')
    ]
