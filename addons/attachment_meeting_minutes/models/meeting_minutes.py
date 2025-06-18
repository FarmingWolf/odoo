# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import datetime

_logger = logging.getLogger(__name__)

class MeetingMinutes(models.Model):
    _name = 'meeting.minutes'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'analytic.mixin']
    _description = '会议纪要'
    _order = 'department_id ASC, meeting_time DESC'

    name = fields.Char(string='名称', compute="_compute_meeting_minutes_name", tracking=True)
    type = fields.Many2one(string='分类', required=True, comodel_name='meeting.minutes.type',
                           default=lambda self: self._get_default_type(), tracking=True)
    subject = fields.Char(string='会议纪要主题', tracking=True)
    company_id = fields.Many2one(comodel_name='res.company', string="公司", required=True, readonly=True, tracking=True,
                                 default=lambda self: self.env.company)
    meeting_time = fields.Datetime(string="会议时间", default=lambda self: fields.Datetime.now(), tracking=True)
    meeting_time_end = fields.Datetime(string="会议结束时间", tracking=True,
                                       default=lambda self: (fields.Datetime.now() + datetime.timedelta(hours=2)))
    department_id = fields.Many2one('hr.department', string="单位", tracking=True,
                                    help='指定单位专用。如不指定，则所有单位都可以使用。',
                                    domain=lambda self: self._get_department_domain(),
                                    default=lambda self: self.env.user.employee_id.department_id)

    def _get_department_domain(self):
        domain = [('company_id', '=', self.env.user.company_id.id)]

        if not self.env.user.has_group('attachment_meeting_minutes.group_meeting_minutes_manager'):
            domain.append(('complete_name', 'ilike', str(self.env.user.employee_id.department_id.complete_name) + '%'))

        return domain

    @api.depends('type', 'subject')
    def _compute_meeting_minutes_name(self):
        for record in self:
            record.name = (record.type.name if record.type else " ") + '-' + (record.subject if record.subject else " ")

    def _get_default_type(self):
        default_type = self.env['meeting.minutes.type'].search([], limit=1)
        if default_type:
            return default_type[0]
        else:
            return False

    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee and not self.env.user.has_group('attachment_meeting_minutes.group_meeting_minutes_user'):
            raise ValidationError('当前用户尚无管理权限. 请联系管理员.')
        return employee

    employee_id = fields.Many2one(comodel_name='hr.employee', string="上传者", default=_default_employee_id,
                                  store=True, check_company=True)
    active = fields.Boolean(string='有效', default=True)
    attachment_id = fields.Many2many('ir.attachment', string="文件", copy=False, required=True)
    nb_attachment = fields.Integer(string="文件数", compute='_compute_nb_attachment')

    @api.depends("attachment_id")
    def _compute_nb_attachment(self):
        attachment_data = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'meeting.minutes'), ('res_id', 'in', self.ids)],
            ['res_id'],
            ['__count'],
        )
        attachment = dict(attachment_data)
        for meeting_minutes in self:
            meeting_minutes.nb_attachment = attachment.get(meeting_minutes._origin.id, 0)


    def _unlink_meeting_minutes_attach(self):
        attachments_to_unlink = self.env['ir.attachment']
        checksums = set(self.attachment_id.mapped('checksum'))
        attachments_to_unlink += self.attachment_id.filtered(lambda att: att.checksum in checksums)
        attachments_to_unlink.unlink()

    def unlink(self):
        self._unlink_meeting_minutes_attach()
        return super().unlink()

    def write(self, vals):
        res = super().write(vals)
        # 检查初始化页面，附件类型ID为空时上传附件导致的附件res_id为空
        for record in self:
            for attachment in record.attachment_id:
                if not attachment.res_id:
                    _logger.info(f"回填附件的res_id:{record.id}")
                    attachment.res_id = record.id

        if 'attachment_id' in vals:
            # 获取当前记录关联的附件
            current_attachments = self.attachment_id
            # 查找不再关联的附件并删除
            obsolete_attachments = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('id', 'not in', current_attachments.ids)
            ])
            obsolete_attachments.unlink()
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        for record in res:
            for attachment in record.attachment_id:
                if not attachment.res_id:
                    attachment.res_id = record.id
        return res