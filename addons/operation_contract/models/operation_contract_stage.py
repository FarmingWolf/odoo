# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class OperationContractStage(models.Model):
    _name = 'operation.contract.stage'
    _description = '运营合同阶段'
    _order = 'sequence, name'

    name = fields.Char(string='阶段名称', required=True, translate=True)
    description = fields.Text(string='阶段描述', translate=True)
    sequence = fields.Integer('阶段序号', default=0, )
    fold = fields.Boolean(string='看板折叠', default=False)
    pipe_end = fields.Boolean(
        string='结束', default=False,
        help='合同完成后将自动被放置在此阶段。处于此阶段的合同任务阶段标志自动被置为绿色')
    legend_blocked = fields.Char(
        '标红', default=lambda s: _('Blocked'), translate=True, prefetch='legend', required=True,
        help='标红表示本阶段受阻')
    legend_done = fields.Char(
        '标绿', default=lambda s: _('Ready for Next Stage'), translate=True, prefetch='legend', required=True,
        help='标绿表示可进入下阶段')
    legend_normal = fields.Char(
        '正常', default=lambda s: _('In Progress'), translate=True, prefetch='legend', required=True,
        help='正常表示本阶段正常推进中')

    op_department_id = fields.Many2one('hr.department', string="部门", help='选择部门后，限制该阶段只能该部门人员处理。',
                                       domain=lambda self: [('company_id', '=', self.env.user.company_id.id)])
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '阶段名称不能重复'),
        ('sequence', 'unique(sequence, company_id)', '阶段序号不能重复'),
    ]
