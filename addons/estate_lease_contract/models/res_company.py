# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    one_year_days = fields.Integer(string='一年天数', default=365, required=True)
    company_nm_4_big_screen = fields.Char(string='大屏用公司名')
