# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class EstateRegistrationAddr(models.Model):

    _name = "estate.registration.addr"
    _description = "注册地址"

    name = fields.Char('注册地址', required=True)
    price = fields.Float('价格（元）')
    sequence = fields.Integer("排序", default=1)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '注册地址不能重复'),
    ]
