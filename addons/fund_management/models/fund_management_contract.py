# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random
import re
from datetime import datetime
from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class FundManagementContract(models.Model):
    _name = "fund.management.contract"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'analytic.mixin']
    _description = "Fund Management Contract"
    _order = "name asc, contract_amount asc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee and not self.env.user.has_group('fund_management.group_fund_management_team_approver'):
            raise ValidationError(_('The current user has no related employee. Please, create one.'))
        return employee

    @api.depends('company_id')
    def _compute_employee_id(self):
        if not self.env.context.get('default_employee_id'):
            for expense in self:
                expense.employee_id = self.env.user.with_company(expense.company_id).employee_id

    name = fields.Char("Contract Name", required=True, index=True, tracking=True)
    contract_no = fields.Char("Contract Number", required=True, index=True, tracking=True)
    contract_amount = fields.Float("Contract Amount", digits=(16, 2), required=True, tracking=True)
    fund_type = fields.Many2one(comodel_name='fund.management.fund.type', string="Fund Type", required=True, tracking=True)
    procurement_method = fields.Many2one(comodel_name='fund.management.procurement.method', string="Procurement Method", required=True, tracking=True)
    account_subject_category = fields.Many2one(comodel_name='accounting.subject.subject', string="Account Subject Category", required=True, tracking=True)
    receiving_unit = fields.Many2one(comodel_name='res.partner', string="Receiving Unit", required=True, tracking=True)
    receiving_bank = fields.Many2one(comodel_name="res.partner.bank", string="Receiving Bank", required=True, tracking=True)
    bank_account = fields.Char(string="Bank Account Number", related="receiving_bank.acc_number", required=True, tracking=True)
    payment_method = fields.Many2one(comodel_name='fund.management.payment.method', string="Payment Method", required=True, tracking=True)
    party_a_unit = fields.Many2one(comodel_name='res.partner', string="Party A Unit", required=True, tracking=True)
    date_sign = fields.Date(string="Sign Date", required=True, tracking=True)
    date_start = fields.Date(string="Start Date", required=True, tracking=True)
    date_end = fields.Date(string="End Date", required=True, tracking=True)

    employee_id = fields.Many2one(comodel_name='hr.employee', string="Employee", compute='_compute_employee_id',
                                  precompute=True, store=True, readonly=False, required=True, default=_default_employee_id,
                                  check_company=True, domain=[('filter_for_fund_management', '=', True)])
    company_id = fields.Many2one(comodel_name='res.company', string="Company", required=True, readonly=True, default=lambda self: self.env.company)

    fund_management_id = fields.One2many('fund.management', required=True,
                                         index=True, string="Fund Management", inverse_name="contract_id")
    _sql_constraints = [
        ('contract_no', 'unique(contract_no)', _('Contract Number must be unique.')),
        ('name', 'unique(name)', _('Contract Name must be unique.'))
    ]
