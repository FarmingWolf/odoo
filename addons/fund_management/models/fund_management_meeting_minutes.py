# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.tools.translate import _
from datetime import datetime

_logger = logging.getLogger(__name__)

class FundManagementMeetingMinutes(models.Model):

    _name = "fund.management.meeting.minutes"
    _description = "Meeting minutes"
    _order = "id ASC"

    @api.model
    def _get_default_name(self):
        tmp_str = _("Meeting Minutes") + fields.Datetime.context_timestamp(self,
                                                                           datetime.now()).strftime('%Y%m%d%H%M%S')
        if self.type:
            return str(self.type.name) + tmp_str

        return tmp_str

    name = fields.Char(string='Meeting Minutes', default=lambda self: self._get_default_name())

    fund_management_id = fields.Many2one(string="Fund Management", comodel_name="fund.management")
    category_id = fields.Many2one(string="Fund Management Category", related="fund_management_id.category_id")
    stage_id = fields.Many2one(string="Fund Management Stage", related="fund_management_id.stage")
    type_domain = fields.Many2many(string="Meeting Minutes Type By Stage", related="stage_id.meeting_minute_types")
    type = fields.Many2one(string="Meeting Minutes Type", comodel_name="fund.management.meeting.minutes.type")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    nb_attachment = fields.Integer(string="Number of Attachments", compute='_compute_nb_attachment')
    attachment_ids = fields.Many2many('ir.attachment', string="Attachment", copy=False, tracking=True)

    @api.onchange("type")
    def _onchange_type(self):
        for record in self:
            if record.type:
                if record.type not in record.name:
                    tmp_str = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d%H%M%S')
                    record.name = str(self.type.name) + _("Meeting Minutes") + tmp_str

    @api.depends("attachment_ids")
    def _compute_nb_attachment(self):
        attachment_data = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'fund.management.meeting.minutes'), ('res_id', 'in', self.ids)],
            ['res_id'],
            ['__count'],
        )
        attachment = dict(attachment_data)
        for meeting_minutes in self:
            meeting_minutes.nb_attachment = attachment.get(meeting_minutes._origin.id, 0)

    def _unlink_meeting_minutes_attach(self):
        attachments_to_unlink = self.env['ir.attachment']
        checksums = set(self.attachment_ids.mapped('checksum'))
        attachments_to_unlink += self.attachment_ids.filtered(lambda att: att.checksum in checksums)
        attachments_to_unlink.with_context(sync_attachment=False).unlink()

    @api.model
    def unlink(self):
        self._unlink_meeting_minutes_attach()
        return super().unlink()

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals:
            # 获取当前记录关联的附件
            current_attachments = self.attachment_ids
            # 查找不再关联的附件并删除
            obsolete_attachments = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('id', 'not in', current_attachments.ids)
            ])
            obsolete_attachments.unlink()
        return res
