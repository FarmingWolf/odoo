# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random
import re
from datetime import datetime
from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ContractExpense(models.Model):

    _name = 'contract.expense'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'analytic.mixin', 'contract.expense']
    _description = 'Contract Expense'

    fund_management_id = fields.One2many('fund.management', required=True,
                                         index=True, string="Fund Management", inverse_name="contract_expense_id")
    this_editable = fields.Boolean(default=True, compute='_compute_this_editable')

    @api.depends('fund_management_id')
    def _compute_this_editable(self):
        for record in self:
            is_editable = False
            if record.employee_id == self.env.user.employee_id:
                application_exists = False
                for fund_management in record.fund_management_id:
                    if fund_management.stage.sequence:
                        application_exists = True
                        break

                is_editable = not application_exists
            else:
                is_editable = False

            if is_editable:
                is_editable = record._compute_editable()

            record.this_editable = is_editable
