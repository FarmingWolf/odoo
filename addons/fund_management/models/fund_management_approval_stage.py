# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class FundManagementApprovalStage(models.Model):
    _name = 'fund.management.approval.stage'
    _description = 'Fund management approval stage'
    _order = 'sequence, description'

    name = fields.Char(string='Approval Stage Name', required=True, translate=True)
    description = fields.Text(string='Approval Stage Description', translate=True)
    sequence = fields.Integer('Approval Stage Sequence NO.', default=0, required=True,
                              help="The approval process will progress from small to large according to the approval sequence number. The initial stage number needs to be set to 0, and it is recommended to interval the stage numbers in units of 10")
    fold = fields.Boolean(string='Kanban Folding', default=False)
    pipe_end = fields.Boolean(
        string='Approval End Flag', default=False,
        help='The final stage of the approval process. The application at this stage can only be issued and become effective. Please set the approval end flag for the approval stage with the highest serial number.')
    legend_blocked = fields.Char(
        'Mark in red', default=lambda s: _('Blocked'), translate=True, prefetch='legend', required=True,
        help='Red indicates obstruction in this stage')
    legend_done = fields.Char(
        'Mark in green', default=lambda s: _('Ready for Next Stage'), translate=True, prefetch='legend', required=True,
        help='Green indicates that the next stage can be entered')
    legend_normal = fields.Char(
        'Normal', default=lambda s: _('In Progress'), translate=True, prefetch='legend', required=True,
        help='Normal indicates that this stage is progressing normally')

    op_department_id = fields.Many2one('hr.department', string="Approval Department",
                                       help='Restrict this stage to personnel with approval authority in the department.',
                                       domain=lambda self: [('company_id', '=', self.env.user.company_id.id)])
    op_job_id = fields.Many2one('hr.job', string='Approval Job Position',
                                help="Restrict this stage to specific job position with approval authority in the department.",
                                domain=lambda self: "[('company_id', '=', company_id), "
                                                    "('department_id', '=', op_department_id)]")
    input_meeting_minutes = fields.Boolean(string="Input Meeting Minutes In This Stage", default=False, copy=False)

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    editable = fields.Boolean(default=lambda self: self._compute_editable(), compute='_compute_editable')

    def _compute_editable(self):
        ret_editable = self.env.user.has_group('fund_management.group_fund_management_manager')
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

    category_id = fields.Many2one('fund.management.category',
                                  default=lambda self: self._get_default_category, store=True)

    meeting_minute_types_by_category = fields.Many2many(string="Meeting Minutes Type By Category", copy=False,
                                                        related="category_id.meeting_minute_types")
    # dynamic domain should be set in views not here
    meeting_minute_types = fields.Many2many(
        string="Meeting Minutes Type", comodel_name="meeting.minutes.type", copy=False,
        relation="stage_meeting_minutes_type_relation", column1="stage_id", column2="meeting_minutes_type_id")

    _sql_constraints = [
        ('sequence', 'unique(name, sequence, company_id, category_id)',
         'Name and sequence number can not be duplicated in the category!'),
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

        # ↓↓↓这个校验会使得创建阶段过程中频繁出发提示，灰常门道库萨伊
        # if pipe_end_cnt == 0 and idx > 1:
        #     if not self.pipe_end:  # 貌似来自write的时候，self.search并没有找到刚添加的数据
        #         raise ValidationError(f"最后阶段必须设置结束标志位：{last_name}(序号:{last_sequence})")

    def _check_op_job_id(self):
        """
        如果本节点不要求部门，那么本节点要求的职位名称不能和其他不要求部门的节点的职位名称相同
        """
        # 业务上的确需要相同岗位审批不同节点，取消这段逻辑
        pass
        # for record in self:
        #     if record.op_department_id:
        #         continue
        #
        #     if record.op_job_id:
        #         domain = [('company_id', '=', self.env.user.company_id.id), ('category_id', '=', record.category_id.id),
        #                   ('op_job_id.name', '=', record.op_job_id.name), ('op_department_id', '=', False),
        #                   ('id', '!=', record.id), ('name', '!=', record.name)]
        #         tgt_cnt = self.search_count(domain)
        #         if tgt_cnt > 0:
        #             raise ValidationError(f"在不要求部门的多个节点中，岗位角色名称和阶段名称必须同时相同。这种情况一般是终端组织内部节点。"
        #                                   f"请斟酌岗位角色名相同的节点，使其阶段名称相同，以确保业务上能够理解该设置，"
        #                                   f"避免相同的职位在不同名称的审批节点引起流程混乱。")

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
        record._check_op_job_id()
        return record

    @api.model
    def write(self, vals):
        res = super().write(vals)
        self._check_pipe_end("from_write")

        for record in self:
            record._check_op_job_id()
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
