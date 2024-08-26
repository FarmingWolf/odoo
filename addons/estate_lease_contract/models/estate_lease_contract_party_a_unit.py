# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class EstateLeaseContractPartyAUnit(models.Model):
    _name = "estate.lease.contract.party.a.unit"
    _description = "资产租赁合同甲方单位管理"

    party_a_unit_id = fields.Many2one(comodel_name='res.partner', required=True, copy=False,
                                      default=lambda self: self.env.user.company_id.partner_id, string="甲方单位",
                                      domain=['|', '|', '|',
                                              ('company_id', 'in', lambda self: self.env.user.allowed_company_ids),
                                              ('create_uid', '=', lambda self: self.env.user.id),
                                              ('write_uid', '=', lambda self: self.env.user.id),
                                              '&',
                                              ('create_uid', '=', 1),
                                              ('create_uid', '=', lambda self: self.env.user.id - 1)])
    name = fields.Char(related="party_a_unit_id.name")
    sequence = fields.Integer("排序", default=1)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('party_a_unit_id', 'unique(party_a_unit_id, company_id)', '甲方单位重复'),
    ]
