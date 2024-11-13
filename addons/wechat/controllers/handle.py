
# -*- coding: utf-8 -*-#
# filename: handle.py
import hashlib
import logging

from odoo.http import request
from . import reply
from . import receive

from odoo import http

_logger = logging.getLogger(__name__)


class Handle(http.Controller):

    """接受公众号的text和img消息"""
    @http.route('/wechat/post_msg', type='http', methods=['POST'], auth='public', csrf=False)
    def post(self):
        try:
            web_data = request.httprequest.data.decode('utf-8')
            _logger.info(f"web_data in post:{web_data}")
            if len(web_data) == 0:
                return "success"

            rec_msg = receive.parse_xml(web_data)
            _logger.info(f"rec_msg in post:{rec_msg}")

            if isinstance(rec_msg, receive.Msg) and rec_msg.MsgType == 'text':
                to_user = rec_msg.FromUserName
                from_user = rec_msg.ToUserName
                content = "test"
                reply_msg = reply.TextMsg(to_user, from_user, content)
                return reply_msg.send()
            else:
                _logger.info("暂且不处理")
                return "success"
        except Exception as e:
            _logger.error(e)
            return e
