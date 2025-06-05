# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ParkVehicleModelCategory(models.Model):
    _name = 'park.vehicle.model.category'
    _inherit = 'fleet.vehicle.model.category'

    _description = '车辆类型'
    _order = 'sequence asc, id asc'

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name, company_id)', _('Category name must be unique'))
    ]
