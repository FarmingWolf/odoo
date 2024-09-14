# -*- coding: utf-8 -*-
import hashlib
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WechatHandle(http.Controller):
    @http.route('/wechat/handle', auth='none', methods=['GET'])
    def get(self, **kwargs):
        try:
            _logger.info(kwargs)

            data = kwargs
            if len(data) == 0:
                return "hello, welcome!"

            signature = data.get('signature')
            timestamp = data.get('timestamp')
            nonce = data.get('nonce')
            echo_str = data.get('echostr')
            token = "491tech4wechat9token1"

            in_list = [token, timestamp, nonce]
            in_list.sort()
            _logger.info(f'in_list={in_list}')
            sha1 = hashlib.sha1()
            map(sha1.update, in_list)
            hashcode = sha1.hexdigest()
            _logger.info(f"handle/GET func: hashcode={hashcode}, signature={signature} ")

            if hashcode == signature:
                return echo_str
            else:
                return "hello, welcome!!!"
        except Exception as e:
            _logger.error(e)
            return e

    @http.route('/wechat/qr-code', type='http', auth='public', website=True)
    def get_qr_code(self, **kw):
        # 这个方法应该返回一个包含二维码的响应
        # 你可以使用微信提供的API来生成二维码并返回
        # 这里仅作示例，你需要根据实际情况实现
        return request.render('wechat.qr_code', {})

    @http.route('/wechat/callback', type='http', auth='public', website=True)
    def wechat_callback(self, **kw):
        _logger.info("entering wechat/callback")
        # 这个方法用于处理微信回调
        # 从回调中获取code，然后通过code换取access_token和openid
        # 最终根据openid找到对应的Odoo用户并登录
        code = kw.get('code')
        # 实现获取access_token和openid的逻辑
        # 并使用这些信息登录Odoo用户
        return request.redirect("/web")
