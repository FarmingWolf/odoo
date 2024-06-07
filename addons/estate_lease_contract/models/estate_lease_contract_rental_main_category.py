# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractRentalMainCategory(models.Model):

    """
    主题集合店、烧烤、饮品烘焙、休闲娱乐、百货、儿童、洋快餐、锅类、中餐、自助餐、生活服务、异国餐饮、影城、鞋品箱包、家居家用、个人护理、儿童零售、
    男装、杂品配饰、时尚潮流、超市、专业美护、运动、简餐、家电、女装、医疗保健、文化娱乐、数码电子、运动集合、儿童教育、主题餐厅、黄金珠宝、大酒楼、
    儿童娱乐、儿童服务、男女集合、教育培训、钟表、烟酒食品、美食广场
    """
    _name = "estate.lease.contract.rental.main.category"
    _description = "主品类"
    _order = "sequence"

    name = fields.Char('主品类', required=True)
    sequence = fields.Integer('排序', default=1)

    _sql_constraints = [
        ('name', 'unique(name)', '主品类不能重复')
    ]
