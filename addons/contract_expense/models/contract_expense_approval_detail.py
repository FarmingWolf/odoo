# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from typing import Dict, List

from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)

class ContractExpenseApprovalDetail(models.Model):
    _name = "contract.expense.approval.detail"
    _description = "支出类合同审批明细"
    _order = "id DESC"

    contract_expense_id = fields.Many2one('contract.expense', string="审批详情", ondelete="restrict")
    approved_by_id = fields.Many2one('hr.employee', string='审批人', default=lambda self: self._get_employee(),
                                     domain="[('company_id', '=', company_id)]")
    approved_by_nm = fields.Char(string='审批人姓名')
    approval_stage = fields.Many2one('contract.expense.approval.stage', string="审批节点")
    approval_stage_id = fields.Integer(string="审批节点ID")
    approval_stage_nm = fields.Char(string="审批节点名")
    approval_comments = fields.Char(string="审批意见")
    approval_decision = fields.Boolean(string="审批决定 Y/N")
    approval_decision_txt = fields.Char(string="审批结果")
    approval_date_time = fields.Datetime(string="审批时间")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.model
    def _get_employee(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            return user.employee_ids[0].id  # 返回第一个employee记录ID
        else:
            return False  # 如果没有employee记录，则返回False

    def create_overdue_records(self):
        tgt_applications = self.env['contract.expense'].sudo().search([('state', 'in', ['submitted', 'approved', 'refused'])])
        for tgt_application in tgt_applications:

            if (tgt_application.category_id.overdue_reminder_hours <= 0) or (not tgt_application.category_id.overdue_reminder_hours):
                continue

            approval_details = self.sudo().search([('contract_expense_id', '=', tgt_application.id)], limit=1, order='id DESC')
            for detail in approval_details:
                if detail.approval_stage.pipe_end:
                    continue
                seconds_lasted = (fields.Datetime.now() - detail.approval_date_time).total_seconds()
                if seconds_lasted > tgt_application.category_id.overdue_reminder_hours * 3600:
                    tgt_tbl = 'contract.expense.overdue'
                    tgt_domain = [('contract_expense_id', '=', tgt_application.id),
                                  ('stage', '=', tgt_application.stage.id),
                                  ('sms_created', '=', False)]
                    overdue_records = self.env[tgt_tbl].sudo().search(tgt_domain)
                    for overdue_old in overdue_records:
                        overdue_old.active = False

                    overdue_record = {'contract_expense_id': tgt_application.id}
                    self.env['contract.expense.overdue'].sudo().create(overdue_record)
