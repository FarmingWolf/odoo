# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.tools.translate import _
from datetime import datetime

_logger = logging.getLogger(__name__)

class ContractExpenseAttachment(models.Model):

    _name = "contract.expense.attachment"
    _description = "支出类合同附件"
    _order = "id ASC"

    @api.model
    def _get_default_name(self):
        tmp_str = "合同附件" + fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d%H%M%S')
        if self.type:
            return str(self.type.name) + tmp_str

        return tmp_str

    name = fields.Char(string='名称', default=lambda self: self._get_default_name())

    contract_expense_id = fields.Many2one(string="合同", comodel_name="contract.expense")
    category_id = fields.Many2one(string="合同流程分类", related="contract_expense_id.category_id")
    stage_id = fields.Many2one(string="合同审批节点", related="contract_expense_id.stage")
    type_domain = fields.Many2many(string="节点附件", related="stage_id.meeting_minute_types")
    type = fields.Many2one(string="附件类别", comodel_name="meeting.minutes.type", required=True, default=type_domain)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    nb_attachment = fields.Integer(string="附件数", compute='_compute_nb_attachment')
    attachment_ids = fields.Many2many('ir.attachment', string="附件", copy=False)

    @api.onchange("type")
    def _onchange_type(self):
        if self.type:
            if self.type.name not in self.name:
                tmp_str = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d%H%M%S')
                self.name = str(self.type.name) + "附件" + tmp_str

    @api.depends("attachment_ids")
    def _compute_nb_attachment(self):
        attachment_data = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'contract.expense.attachment'), ('res_id', 'in', self.ids)],
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

    @api.model
    def create(self, vals):
        res = super().create(vals)
        for record in res:
            for attachment in record.attachment_ids:
                if not attachment.res_id:
                    attachment.res_id = record.id
        return res