# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Users(models.Model):

    _name = 'res.users'
    _inherit = ['res.users']

    property_ids = fields.One2many('estate.property', 'sales_person_id', string="销售员",
                                   domain="[('active', '=', 'true')]")
