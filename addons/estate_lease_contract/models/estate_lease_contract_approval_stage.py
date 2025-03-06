# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError


class EstateLeaseContractApprovalStage(models.Model):
    _name = 'estate.lease.contract.approval.stage'
    _description = '租赁合同审批阶段'
    _order = 'sequence, name'

    name = fields.Char(string='审批阶段名称', required=True, translate=True)
    description = fields.Text(string='审批阶段描述', translate=True)
    sequence = fields.Integer('审批阶段序号', default=0, help="审批流将按照审批序号由小到大推进审批阶段。初始阶段序号需设置为0")
    fold = fields.Boolean(string='看板折叠', default=False)
    pipe_end = fields.Boolean(
        string='审批结束标志位', default=False,
        help='审批流程的最后阶段。处于此阶段的租赁合同方可发布生效。请将最大序号的审批阶段设置审批结束标志。')
    legend_blocked = fields.Char(
        '标红', default=lambda s: _('Blocked'), translate=True, prefetch='legend', required=True,
        help='标红表示本阶段受阻')
    legend_done = fields.Char(
        '标绿', default=lambda s: _('Ready for Next Stage'), translate=True, prefetch='legend', required=True,
        help='标绿表示可进入下阶段')
    legend_normal = fields.Char(
        '正常', default=lambda s: _('In Progress'), translate=True, prefetch='legend', required=True,
        help='正常表示本阶段正常推进中')

    op_department_id = fields.Many2one('hr.department', string="审批部门", help='限制该阶段只能该部门中具有审批权限的人员处理。',
                                       domain=lambda self: [('company_id', '=', self.env.user.company_id.id)])
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '阶段名称不能重复'),
        ('sequence', 'unique(sequence, company_id)', '阶段序号不能重复'),
    ]

    @api.constrains('sequence', 'pipe_end')
    def _check_pipe_end(self):
        records = self.search([('company_id', '=', self.env.user.company_id.id)])
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
