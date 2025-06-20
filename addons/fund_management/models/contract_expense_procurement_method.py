# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import _


class ContractExpenseProcurementMethod(models.Model):
    """
    公开招标、竞争性谈判、必选、其他
    """
    _name = 'contract.expense.procurement.method'
    _inherit = "contract.expense.procurement.method"

    editable = fields.Boolean(default=lambda self: self._compute_editable(), compute='_compute_editable')

    def _compute_editable(self):
        ret_editable = self.env.user.has_group('fund_management.group_fund_management_manager')
        self.editable = ret_editable
        return ret_editable
