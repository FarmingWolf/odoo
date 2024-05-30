# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractType(models.Model):

    _name = "estate.lease.contract.type"
    _description = "资产租赁合同类型"
    _order = "sequence"

    name = fields.Char('资产租赁合同类型', required=True)
    contract_ids = fields.One2many('estate.lease.contract', 'contract_type_id', string="合同")
    sequence = fields.Integer('Sequence', default=1, help="按类型排序")

    _sql_constraints = [
        ('name', 'unique(name)', '合同类型不能重复')
    ]
