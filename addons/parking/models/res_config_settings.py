# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    vehicle_number_limit = fields.Integer(string='车辆管理上限', default=100, config_parameter='hr_fleet.vehicle_number_limit')
