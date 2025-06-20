# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import _


class ContractExpenseFundType(models.Model):
    """
    财政专项资金、集体资金
    """
    _name = "contract.expense.fund.type"
    _description = "合同支出资金类型"
    _order = "sequence ASC"

    name = fields.Char('资金类型', required=True)
    sequence = fields.Integer('sequence', default=1)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '类型名不能重复')
    ]
