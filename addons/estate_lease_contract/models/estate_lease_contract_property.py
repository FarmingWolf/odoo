# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstateLeaseContractProperty(models.Model):

    _name = 'estate.lease.contract.property'
    _description = "资产租赁合同租赁标的"
    _inherit = ['estate.property']

    rent_plan_id = fields.Many2one('estate.lease.contract.rental.plan', string="租金方案")
    management_fee_plan_id = fields.Many2one('estate.lease.contract.property.management.fee.plan', string="物业费方案")
