# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import _


class ContractExpensePaymentMethod(models.Model):
    """
    网银转账、支票、现金
    """
    _name = "contract.expense.payment.method"
    _description = "支付方式"
    _order = "sequence"

    name = fields.Char('支付方式', required=True)
    sequence = fields.Integer('sequence', default=1)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '名称不能重复')
    ]
