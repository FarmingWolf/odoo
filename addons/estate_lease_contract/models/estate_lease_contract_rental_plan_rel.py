# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class EstateLeaseContractRentalPlanRel(models.Model):

    _name = 'estate.lease.contract.rental.plan.rel'
    _description = "合同-资产-租金方案关系表"
    _order = "id"

    contract_id = fields.Many2one('estate.lease.contract', string='合同', required=True)
    property_id = fields.Many2one('estate.property', string='资产', required=True)
    rental_plan_id = fields.Many2one('estate.lease.contract.rental.plan', string='租金方案')

    _sql_constraints = [
        ('contract_property_rental_plan_unique', 'unique(contract_id, property_id)',
         "同一合同内，同一资产，不能有不同的租金方案"),
    ]
