# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ContractExpenseApprovalStage(models.Model):
    _name = 'contract.expense.approval.stage'
    _description = '支付类合同按审批流种类设置节点'
    _order = 'sequence, description'

    name = fields.Char(string='节点名', required=True, translate=True)
    description = fields.Text(string='节点描述', translate=True)
    sequence = fields.Integer('节点序号', default=0, required=True,
                              help="流程节点根据序号从小到大流转。 最小节点序号必须为0！建议节点序号以10为单位增加。")
    fold = fields.Boolean(string='看板折叠', default=False)
    pipe_end = fields.Boolean(string='流程结束标识', default=False)
    legend_blocked = fields.Char(
        '标红', default=lambda s: '受阻', translate=True, prefetch='legend', required=True,
        help='红色标识本节点受阻')
    legend_done = fields.Char(
        '标绿', default=lambda s: '可进入下节点', translate=True, prefetch='legend', required=True,
        help='绿色表示可进入下一节点')
    legend_normal = fields.Char(
        '正常', default=lambda s: '处理中', translate=True, prefetch='legend', required=True)

    op_department_id = fields.Many2one('hr.department', string="审批部门", help='审批人需在此部门',
                                       domain=lambda self: [('company_id', '=', self.env.user.company_id.id)])
    op_job_id = fields.Many2one('hr.job', string='审批岗位/职位/角色',
                                domain=lambda self: "[('company_id', '=', company_id), "
                                                    "('department_id', '=', op_department_id)]")
    input_meeting_minutes = fields.Boolean(string="本节点输入附件（如会议纪要等）", default=False, copy=False)

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    editable = fields.Boolean(default=lambda self: self._compute_editable(), compute='_compute_editable')

    def _compute_editable(self):
        ret_editable = self.env.user.has_group('contract_expense.group_contract_expense_manager')
        self.editable = ret_editable
        return ret_editable

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            defaults['category_id'] = active_id

        default_category = self.env.context.get('default_category_id')

        if default_category:
            defaults['category_id'] = default_category

        _logger.info(f"in default_get active_id={active_id};default_category={default_category}")

        return defaults

    def _get_default_category(self):
        default_category_id = self.env.context.get('default_category_id')
        active_category_id = self.env.context.get('active_id')
        _logger.info(f"default_category_id={default_category_id};active_category_id={active_category_id}")
        return default_category_id

    category_id = fields.Many2one('contract.expense.category',
                                  default=lambda self: self._get_default_category, store=True)

    meeting_minute_types_by_category = fields.Many2many(string="会议纪要等附件种类", copy=False,
                                                        related="category_id.meeting_minute_types")
    # dynamic domain should be set in views not here
    meeting_minute_types = fields.Many2many(
        string="会议纪要种类", comodel_name="meeting.minutes.type", copy=False,
        relation="c_stage_meeting_minutes_type_relation", column1="stage_id", column2="meeting_minutes_type_id")

    _sql_constraints = [
        ('sequence', 'unique(name, sequence, company_id, category_id)', '节点名称和序号不可重复！'),
    ]

    def _check_pipe_end(self, from_method):
        _logger.info(f"{from_method},{self.ids}")
        records = self.search([('company_id', '=', self.env.user.company_id.id),
                               ('category_id', '=', self.category_id.id)], order="sequence, description")
        pipe_end_cnt = 0
        msg = []
        last_name = ""
        end_flag_name = ""
        end_flag_sequence = 0
        last_sequence = 0
        idx = 0
        for record in records:
            if idx == 0:
                if record.sequence != 0:
                    raise ValidationError(f"第一个审批阶段[{record.name}]的阶段序号必须为0")
            if idx == 1:
                if record.sequence < 10:
                    raise ValidationError(f"第二个及更靠后的审批阶段[{record.name}]的阶段序号必须>=10")

            if pipe_end_cnt >= 1:
                raise ValidationError(f"非最后阶段不能设置结束标志位：{end_flag_name}(序号：{end_flag_sequence})")

            if record.pipe_end:
                pipe_end_cnt += 1
                end_flag_name = record.name
                end_flag_sequence = record.sequence
                msg.append(record.name)

            last_name = record.name
            last_sequence = record.sequence
            idx += 1

        _logger.info(f"len(records)={idx}")
        if last_name in msg:
            msg.remove(last_name)

        if pipe_end_cnt > 1:
            raise ValidationError(f"只能将最后一个审批阶段[{last_name}]标记审批结束标志位。请取消{msg}的审批结束标志位。")

    def copy(self, default=None):

        if default is None:
            default = {}

        default.update({
            'name': self.name + "(阶段名称已复制，请修改！)",
            'sequence': self.sequence + 10
        })
        return super().copy(default)

    @api.model
    def create(self, vals_list):
        if 'sequence' in vals_list:
            if vals_list['sequence'] > 0:
                if ('pipe_end' in vals_list) and (vals_list['pipe_end']):
                    if (('op_department_id' or 'op_job_id') in vals_list) and \
                            (vals_list['op_department_id'] or vals_list['op_job_id']):
                        raise ValidationError(f"请勿同时设置阶段的结束标志和审批部门与角色职位。"
                                              f"阶段:{vals_list['name']}(序号:{vals_list['sequence']})")
                elif ('pipe_end' in vals_list) and (not vals_list['pipe_end']):
                    # 可仅设置部门或仅设置角色以应对多个部门相同角色的审核需求，如：企业负责人（经理）审批，企业不定
                    if (('op_department_id' and 'op_job_id') not in vals_list) or \
                            (not vals_list['op_department_id'] and not vals_list['op_job_id']):
                        raise ValidationError(f"请设置非结束阶段的审批部门或角色职位。"
                                              f"阶段：{vals_list['name']}(序号:{vals_list['sequence']})")

        record = super().create(vals_list)
        record._check_pipe_end("from_create")
        return record

    @api.model
    def write(self, vals):
        res = super().write(vals)
        self._check_pipe_end("from_write")

        for record in self:
            if record.sequence > 0:
                if not record.pipe_end:
                    if (not record.op_department_id) and (not record.op_job_id):
                        raise ValidationError(f"请设置非结束阶段的审批部门或角色职位。"
                                              f"阶段：{record.name}(序号:{record.sequence})")
                else:
                    if record.op_department_id or record.op_job_id:
                        raise ValidationError(f"请勿同时设置阶段的结束标志位和审批部门与角色职位信息。"
                                              f"阶段:{record.name}(序号:{record.sequence})")

        return res
