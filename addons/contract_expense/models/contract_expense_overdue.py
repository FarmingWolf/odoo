# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class ContractExpenseOverdue(models.Model):

    _name = "contract.expense.overdue"
    _description = "超期未处理合同"
    _order = "overdue_hours DESC, category_id ASC"

    contract_expense_id = fields.Many2one(comodel_name="contract.expense")
    contract_no = fields.Char(related="contract_expense_id.contract_no", store=True)
    contract_no_suffix = fields.Char(string="合同编号后缀", compute="_compute_contract_no_suffix", store=True)
    name = fields.Char(related='contract_expense_id.name', store=True)
    category_id = fields.Many2one(comodel_name='contract.expense.category', related='contract_expense_id.category_id', store=True)
    overdue_reminder_hours = fields.Float(related='category_id.overdue_reminder_hours', store=True)
    apply_date = fields.Date(related='contract_expense_id.date_apply', store=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', related="contract_expense_id.employee_id", store=True)
    applicant_unit = fields.Char(comodel_name='hr.department', related="contract_expense_id.department_id.name", store=True)
    category_description = fields.Text(related='contract_expense_id.category_description', store=True)
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="货币",
        readonly=True,
    )
    contract_amount = fields.Float(related="contract_expense_id.contract_amount", store=True)
    state = fields.Selection(
        selection=[
            ('draft', 'To Submit'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('refused', 'Refused'),
            ('stopped', 'Stopped')
        ], related='contract_expense_id.state', store=True)
    latest_approval_detail_id = fields.Many2one("contract.expense.approval.detail", string="最新审批详情",
                                                compute="_compute_latest_approval_detail", store=True, precompute=True)
    stage = fields.Many2one('contract.expense.approval.stage', related='latest_approval_detail_id.approval_stage', store=True)
    approval_decision_txt = fields.Char(related='latest_approval_detail_id.approval_decision_txt', store=True)
    receive_datetime = fields.Datetime(related='latest_approval_detail_id.approval_date_time', store=True)
    check_datetime = fields.Datetime(string="超期检查时间", default=fields.Datetime.now)
    overdue_hours = fields.Float(string='超期小时数', compute="_compute_overdue_hours", store=True)
    overdue_description = fields.Char(string='超期详情', compute="_compute_overdue_description", store=True)
    receive_employee_id = fields.Many2one(comodel_name='hr.employee', compute="_compute_receive_employee_id", store=True)
    receive_mobile = fields.Char(related="receive_employee_id.mobile_phone", store=True)
    sms_created = fields.Boolean(string='短信做成', default=False)

    company_id = fields.Many2one(comodel_name='res.company', related='contract_expense_id.company_id', store=True)
    active = fields.Boolean(default=True)

    @api.depends('contract_no')
    def _compute_contract_no_suffix(self):
        for record in self:
            record.contract_no_suffix = record.contract_no.rpartition('-')[2]

    @api.depends('contract_expense_id')
    def _compute_latest_approval_detail(self):
        for record in self:
            details = self.env['contract.expense.approval.detail'].sudo().search([('contract_expense_id', '=',
                                                                                   record.contract_expense_id.id)],
                                                                                 limit=1, order='id DESC')
            for detail in details:
                record.latest_approval_detail_id = detail.id

    @api.depends('receive_datetime', 'check_datetime')
    def _compute_overdue_hours(self):
        for record in self:
            record.overdue_hours = (record.check_datetime - record.receive_datetime).total_seconds() // 3600

    @api.depends('overdue_hours')
    def _compute_overdue_description(self):
        for record in self:
            if record.overdue_hours > 24:
                record.overdue_description = f"{int(record.overdue_hours // 24)}天"
            else:
                record.overdue_description = f"{int(record.overdue_hours)}小时"

    @api.depends('stage')
    def _compute_receive_employee_id(self):
        for record in self:
            s_domain = [('company_id', '=', record.stage.company_id.id)]
            if record.stage.op_department_id:
                s_domain.append(('department_id', '=', record.stage.op_department_id.id))
            # 有可能job_id不同但是name相同
            # if record.stage.op_job_id:
            #     s_domain.append(('job_id', '=', record.stage.op_job_id.id))
            tgt_employees = self.env['hr.employee'].sudo().search(s_domain, order='id DESC')
            for tgt_employee in tgt_employees:
                # 找寻具有本stage权限的employee
                if not tgt_employee.user_id.has_group('contract_expense.group_contract_expense_user'):
                    continue

                # 基本原则是管控住平级企业间数据隔离
                # 如果有部门要求，那么该条件自然带入到搜索条件中，所以这里看无部门要求的stage
                if not record.stage.op_department_id:
                    # 无部门要求指的是：经办人与审批人在同一条部门路径上，而审批人必须得有部门，否则不符常规
                    if tgt_employee.department_id.complete_name and (tgt_employee.department_id.complete_name not in record.employee_id.department_id.complete_name):
                        continue

                    if record.stage.op_job_id:
                        if record.stage.op_job_id.id == tgt_employee.job_id.id or record.stage.op_job_id.name == tgt_employee.job_title:
                            record.receive_employee_id = tgt_employee.id
                            break
                    else:  # 理论上同时不要求部门和职位的阶段只有开始和结束stage，而end_stage到不了这里，所以这里直接给到提交人
                        record.receive_employee_id = record.employee_id
                        break
                else:
                    if record.stage.op_job_id:
                        if record.stage.op_job_id.id == tgt_employee.job_id.id or record.stage.op_job_id.name == tgt_employee.job_title:
                            record.receive_employee_id = tgt_employee.id
                            break
                    else:  # 有部门要求但是没有职位要求，那么筛选出来的结果集到这里的都符合要求
                        record.receive_employee_id = tgt_employee.id
                        break
