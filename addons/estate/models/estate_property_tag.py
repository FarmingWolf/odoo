# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstatePropertyTag(models.Model):

    _name = "estate.property.tag"
    _description = "资产标签"

    name = fields.Char('资产标签', required=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '资产标签不能重复')
    ]
