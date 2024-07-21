# -*- coding: utf-8 -*-

from odoo import api, models, SUPERUSER_ID, fields
from odoo.exceptions import AccessError


class EventEvent(models.Model):
    _inherit = 'event.event'

    event_map = fields.Image(string='活动地图', max_width=1024, max_height=1024)
    event_location_id = fields.Many2many('event.track.location', 'even_location_rel', 'event_id', 'location_id',
                                         string='Event Location', copy=False)
    stage_id_sequence = fields.Integer(store=False, related='stage_id.sequence', string='stage_id_sequence')

    @api.model
    def check_and_write(self, values):
        """Custom logic to check user permissions before writing."""
        self.ensure_one()
        # 检查当前用户是否属于特定权限组，例如event_supervisor
        if self.env.user.has_group('event_extend.group_event_supervisor') or (
                self._origin and 'cron' in self._origin._name):
            # 活动审批人仅可以操作“待审批→已审批”的流程

            return super(EventEvent, self).write(values)
        else:
            # 如果用户无权更改状态，可以抛出错误或采取其他措施
            raise AccessError(f"{self.env.user}您不能直接修改活动状态！请联系活动审批组进行审批！")

    def write(self, values):
        """Override the write method to enforce custom security checks."""
        # 如果stage_id被修改，则先进行权限检查
        if 'stage_id' in values:
            for record in self:
                record.check_and_write(values)
        else:
            # 对于非stage_id的写入操作，直接调用父类方法
            return super(EventEvent, self).write(values)

    def action_print_venue_application(self):
        return self.env.ref('event_extend.action_print_venue_application').report_action(self)

    def action_print_entry_exit_form(self):
        return self.env.ref('event_extend.action_print_entry_exit_form').report_action(self)
