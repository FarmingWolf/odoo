# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractRentalPlan(models.Model):

    _name = "estate.lease.contract.rental.plan"
    _description = "资产租赁合同租金方案"
    _order = "sequence"

    name = fields.Char('资产租赁合同租金方案', required=True)
    contract_ids = fields.One2many('estate.lease.contract', 'rental_plan_id', string="合同")
    sequence = fields.Integer('Sequence', default=1, help="按类型排序")

    _sql_constraints = [
        ('name', 'unique(name)', '租金方案名不能重复')
    ]
