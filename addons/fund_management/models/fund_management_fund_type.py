# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import _


class FundManagementFundType(models.Model):
    """
    财政专项资金、集体资金
    """
    _name = "fund.management.fund.type"
    _description = "Fund Management Fund Type"
    # _order 属性指定了记录在视图中显示的顺序。
    _order = "sequence"

    name = fields.Char('Fund Type', required=True)
    sequence = fields.Integer('sequence', default=1)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    editable = fields.Boolean(default=False, compute='_compute_editable')

    def _compute_editable(self):
        self.editable = self.env.user.has_group('fund_management.group_fund_management_manager')

    _sql_constraints = [
        ('name', 'unique(name, company_id)', _('Type name can not be duplicated'))
    ]
