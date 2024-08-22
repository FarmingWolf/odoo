# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class ParkingSpaceType(models.Model):

    _name = "parking.space.type"
    _description = "园区停车位类型"

    name = fields.Char('停车位类型', required=True, translate=True)
    sequence = fields.Integer('排序', default=1, help="排序")
    space_cnt = fields.Integer(string='停车位数量', compute='_compute_parking_space_count')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '类型不能重复')
    ]

    @api.depends('name')
    def _compute_parking_space_count(self):
        for rcd in self:
            rcd.space_cnt = self.env['parking.space'].search_count([('parking_space_type_id', '=', rcd.id)])
