# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WechatMiniprogramSession(models.Model):
    _name = 'wechat.miniprogram.session'
    _description = '微信小程序会话'
    _rec_name = 'token'

    token = fields.Char('会话Token', required=True, index=True)
    open_id = fields.Char('OpenID', required=True, index=True)
    session_key = fields.Char('会话密钥')
    union_id = fields.Char('UnionID')
    create_time = fields.Datetime('创建时间', default=lambda self: fields.Datetime.now())
    expire_time = fields.Datetime('过期时间', required=True)
    last_access_time = fields.Datetime('最后访问时间', default=lambda self: fields.Datetime.now())
    
    _sql_constraints = [
        ('token_unique', 'unique(token)', 'Token必须唯一!')
    ]
    
    def clean_expired_sessions(self):
        """清理过期的会话"""
        expired = self.search([
            ('expire_time', '<', fields.Datetime.now())
        ])
        if expired:
            expired.unlink()
        return True 