# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from typing import Dict, List

from odoo import fields, models, api

_logger = logging.getLogger(__name__)

class FundManagementApprovalDetail(models.Model):
    _name = "fund.management.approval.detail"
    _description = "Fund Management Approval Detail"
    _order = "id DESC"

    fund_management_id = fields.Many2one('fund.management', string="Fund Management Approval", ondelete="restrict")
    approved_by_id = fields.Many2one('hr.employee', string='Approver ID', default=lambda self: self._get_employee(),
                                     domain="[('company_id', '=', company_id)]")
    approved_by_nm = fields.Char(string='Approver')
    approval_stage = fields.Many2one('fund.management.approval.stage', string="Approval Stage")
    approval_stage_id = fields.Integer(string="Approval Stage ID")
    approval_stage_nm = fields.Char(string="Approval Stage")
    approval_comments = fields.Char(string="Approval Comments")
    approval_decision = fields.Boolean(string="Approval Decision Y/N")
    approval_decision_txt = fields.Char(string="Approval Decision")
    approval_date_time = fields.Datetime(string="Approval Datetime")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.model
    def _get_employee(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            return user.employee_ids[0].id  # 返回第一个employee记录ID
        else:
            return False  # 如果没有employee记录，则返回False
