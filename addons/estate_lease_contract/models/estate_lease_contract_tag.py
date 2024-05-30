# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstateLeaseContractTag(models.Model):

    _name = "estate.lease.contract.tag"
    _description = "资产租赁合同标签"

    name = fields.Char('资产租赁合同标签', required=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name', 'unique(name)', '合同标签不能重复')
    ]
