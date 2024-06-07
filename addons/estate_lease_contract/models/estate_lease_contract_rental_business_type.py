# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractRentalBusinessType(models.Model):

    """
    大型零售、餐饮美食、主题体验、大型儿童、体验业态、生活精品、儿童业态、服装服饰、大型餐饮、教育培训、桌面办公
    """
    _name = "estate.lease.contract.rental.business.type"
    _description = "租金方案经营业态"
    _order = "sequence"

    name = fields.Char('租金方案经营业态', required=True)
    sequence = fields.Integer('排序', default=1)

    _sql_constraints = [
        ('name', 'unique(name)', '经营业态不能重复')
    ]
