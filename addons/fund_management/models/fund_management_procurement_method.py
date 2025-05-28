# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import _


class FundManagementProcurementMethod(models.Model):
    """
    公开招标、竞争性谈判、必选、其他
    """
    _name = "fund.management.procurement.method"
    _description = "Procurement Method"
    _order = "sequence"

    name = fields.Char('Procurement Method', required=True)
    sequence = fields.Integer('sequence', default=1)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    editable = fields.Boolean(default=lambda self: self._compute_editable(), compute='_compute_editable')

    def _compute_editable(self):
        ret_editable = self.env.user.has_group('fund_management.group_fund_management_manager')
        self.editable = ret_editable
        return ret_editable

    _sql_constraints = [
        ('name', 'unique(name, company_id)', _('The procurement method can not be duplicated'))
    ]
