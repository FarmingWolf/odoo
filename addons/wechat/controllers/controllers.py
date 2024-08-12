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
