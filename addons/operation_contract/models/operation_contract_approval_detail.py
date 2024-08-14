# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from typing import Dict, List

from odoo import fields, models, api

_logger = logging.getLogger(__name__)

class OperationContractApprovalDetail(models.Model):
    _name = "operation.contract.approval.detail"
    _description = "运营合同审批明细"
    _order = "id DESC"

    contract_id = fields.Many2one('operation.contract.contract', string="运营合同", ondelete="restrict")  # 拒绝删除
    approved_by_id = fields.Many2one('hr.employee', string='审批人ID', default=lambda self: self._get_employee(),
                                     domain="[('company_id', '=', company_id)]")
    approved_by_nm = fields.Char(string='审批人')
    approval_stage = fields.Many2one('operation.contract.stage', string="阶段",
                                     domain=lambda self: [('company_id', '=', self.env.user.company_id.id)])
    approval_stage_id = fields.Integer(string="审批阶段ID")
    approval_stage_nm = fields.Char(string="审批阶段")
    approval_comments = fields.Char(string="审批意见")
    approval_decision = fields.Boolean(string="审批结果Y/N")
    approval_decision_txt = fields.Char(string="审批结果", store="False")
    approval_date_time = fields.Datetime(string="审批日期")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.model
    def _get_employee(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            return user.employee_ids[0].id  # 返回第一个employee记录ID
        else:
            return False  # 如果没有employee记录，则返回False
