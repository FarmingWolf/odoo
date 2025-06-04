# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ParkVehicleTag(models.Model):
    _name = 'park.vehicle.tag'
    _description = 'Park Vehicle Tag'


    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [('name_uniq', 'unique (name)', "Tag name already exists!")]

