# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class FundManagementOverdue(models.Model):

    _name = "fund.management.overdue"
    _description = "Fund Management Overdue"
    _order = "overdue_hours DESC, category_id ASC"

    fund_management_id = fields.Many2one(comodel_name="fund.management")
    apply_no = fields.Char(related="fund_management_id.apply_no", store=True)
    apply_no_suffix = fields.Char(string="Apply Number Suffix", compute="_compute_apply_no_suffix", store=True)
    name = fields.Char(related='fund_management_id.name', store=True)
    category_id = fields.Many2one(comodel_name='fund.management.category', related='fund_management_id.category_id', store=True)
    overdue_reminder_hours = fields.Float(related='category_id.overdue_reminder_hours', store=True)
    contract_payment = fields.Boolean(related='category_id.contract_payment', store=True)
    apply_date = fields.Date(related='fund_management_id.date', store=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', related="fund_management_id.employee_id", store=True)
    applicant_unit = fields.Char(comodel_name='hr.department', related="fund_management_id.applicant_unit", store=True)
    category_description = fields.Text(related='fund_management_id.category_description', store=True)
    description = fields.Text(related='fund_management_id.description', store=True)
    total_amount = fields.Monetary(related='fund_management_id.total_amount', currency_field='company_currency_id', store=True)
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Report Company Currency",
        readonly=True,
    )
    contract_amount = fields.Float(related="fund_management_id.contract_amount", store=True)
    state = fields.Selection(
        selection=[
            ('draft', 'To Submit'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('refused', 'Refused')
        ], related='fund_management_id.state', store=True)
    stage = fields.Many2one('fund.management.approval.stage', related='fund_management_id.stage', store=True)
    latest_approval_detail_id = fields.Many2one("fund.management.approval.detail", string="Latest Approval Detail",
                                                compute="_compute_latest_approval_detail", store=True, precompute=True)
    receive_datetime = fields.Datetime(related='latest_approval_detail_id.approval_date_time', store=True)
    check_datetime = fields.Datetime(string="Check Date Time", default=fields.Datetime.now)
    overdue_hours = fields.Float(string='Overdue Hours', compute="_compute_overdue_hours", store=True)
    overdue_description = fields.Char(string='Overdue Description', compute="_compute_overdue_description", store=True)
    receive_employee_id = fields.Many2one(comodel_name='hr.employee', compute="_compute_receive_employee_id", store=True)
    receive_mobile = fields.Char(related="receive_employee_id.mobile_phone", store=True)
    sms_created = fields.Boolean(string='SMS Message Created', default=False)

    company_id = fields.Many2one(comodel_name='res.company', related='fund_management_id.company_id', store=True)
    active = fields.Boolean(default=True)

    @api.depends('apply_no')
    def _compute_apply_no_suffix(self):
        for record in self:
            record.apply_no_suffix = record.apply_no.rpartition('-')[2]

    @api.depends('fund_management_id')
    def _compute_latest_approval_detail(self):
        for record in self:
            details = self.env['fund.management.approval.detail'].sudo().search([('fund_management_id', '=', record.fund_management_id.id)],
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
                if not tgt_employee.user_id.has_group('fund_management.group_fund_management_team_approver'):
                    continue

                # 基本原则是管控住平级企业间数据隔离
                # 如果有部门要求，那么该条件自然带入到搜索条件中，所以这里看无部门要求的stage
                if not record.stage.op_department_id:
                    # 无部门要求指的是：经办人与审批人在同一条部门路径上
                    if not tgt_employee.department_id.complete_name in record.employee_id.department_id.complete_name:
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
