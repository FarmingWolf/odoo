# -*- coding: utf-8 -*-
import functools
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def validate_token(func):
    """
    验证请求中的token
    使用方法：在需要验证token的接口方法上添加装饰器 @validate_token
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # 获取请求头中的token
        auth_header = request.httprequest.headers.get('Authorization')
        token = None
        
        if auth_header:
            auth_parts = auth_header.split(' ')
            if len(auth_parts) == 2 and auth_parts[0].lower() == 'bearer':
                token = auth_parts[1]
        
        # 如果请求头没有token，尝试从请求参数获取
        if not token and kwargs.get('token'):
            token = kwargs.get('token')
            
        if not token:
            return {'success': False, 'code': 401, 'message': '未提供有效的授权信息'}
            
        # 验证token
        env = request.env
        session = env['wechat.miniprogram.session'].sudo().search([
            ('token', '=', token),
            ('expire_time', '>=', http.request.env['ir.fields.converter']._str_to_datetime(None, None, 
                                                                                          http.request.env['ir.fields.converter']._now()))
        ], limit=1)
        
        if not session:
            return {'success': False, 'code': 401, 'message': '无效的token或已过期'}
            
        # 更新最后访问时间
        session.write({'last_access_time': http.request.env['ir.fields.converter']._now()})
        
        # 获取微信用户
        open_id = session.open_id
        wx_user = env['wechat.users'].sudo().search([('open_id', '=', open_id)], limit=1)
        
        if not wx_user:
            return {'success': False, 'code': 403, 'message': '用户未注册'}
            
        # 将用户信息添加到kwargs
        kwargs['wx_user'] = wx_user
        kwargs['session'] = session
        
        return func(self, *args, **kwargs)
        
    return wrapper 