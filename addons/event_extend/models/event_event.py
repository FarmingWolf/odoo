# -*- coding: utf-8 -*-

from odoo import api, models, SUPERUSER_ID
from odoo.exceptions import AccessError


class EventEvent(models.Model):
    _inherit = 'event.event'

    @api.model
    def check_and_write(self, values):
        """Custom logic to check user permissions before writing."""
        self.ensure_one()
        # 检查当前用户是否属于特定权限组，例如event_supervisor
        if self.env.user.has_group('event_extend.group_event_supervisor'):
            # 在此添加特定逻辑，或直接调用super写入
            return super(EventEvent, self).write(values)
        else:
            # 如果用户无权更改状态，可以抛出错误或采取其他措施
            raise AccessError(f"{self.env.user.groups_id}您不能直接修改活动状态！请联系活动审批组进行审批！请恢复活动状态之后保存其他数据！")

    def write(self, values):
        """Override the write method to enforce custom security checks."""
        # 如果stage_id被修改，则先进行权限检查
        if 'stage_id' in values:
            for record in self:
                record.check_and_write(values)
        else:
            # 对于非stage_id的写入操作，直接调用父类方法
            return super(EventEvent, self).write(values)
