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
    sequence = fields.Integer('Approval Stage Sequence NO.', default=0,
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

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            defaults['category_id'] = active_id

        default_category = self.env.context.get('default_category')

        if default_category:
            defaults['category_id'] = default_category

        _logger.info(f"in default_get active_id={active_id};default_category={default_category}")

        return defaults

    def _get_default_category(self):
        default_category_id = self.env.context.get('default_category')
        active_category_id = self.env.context.get('active_id')
        _logger.info(f"default_category_id={default_category_id};active_category_id={active_category_id}")
        return default_category_id

    category_id = fields.Many2one('fund.management.category',
                                  default=lambda self: self._get_default_category, store=True)

    _sql_constraints = [
        ('sequence', 'unique(name, sequence, company_id, category_id)',
         'Name and stage number can not be duplicated in the category!'),
    ]

    @api.constrains('sequence', 'pipe_end')
    def _check_pipe_end(self):
        records = self.search([('company_id', '=', self.env.user.company_id.id),
                               ('category_id', '=', self.category_id.id)])
        pipe_end_cnt = 0
        not_last_pipe_end = False
        msg = []
        last_name = ""
        idx = 0
        for record in records:
            if idx == 0:
                if record.sequence != 0:
                    raise ValidationError(f"第一个审批阶段[{record.name}]的阶段序号必须为0")
            if idx == 1:
                if record.sequence < 10:
                    raise ValidationError(f"第二个审批阶段[{record.name}]的阶段序号必须>=10")

            if pipe_end_cnt >= 1:
                not_last_pipe_end = True
            if record.pipe_end:
                pipe_end_cnt += 1
                msg.append(record.name)
            last_name = record.name
            idx += 1

        if last_name in msg:
            msg.remove(last_name)
        if (pipe_end_cnt > 1) or not_last_pipe_end:
            raise ValidationError(f"只能将最后一个审批阶段[{last_name}]标记审批结束标志位。请取消{msg}的审批结束标志位。")

    def copy(self, default=None):

        if default is None:
            default = {}

        default.update({
            'name': self.name + "(阶段名称已复制，请修改！)",
            'sequence': self.sequence + 10
        })
        return super().copy(default)
