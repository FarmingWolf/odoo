import logging

from .controllers import get_wx_user
from odoo import http
from odoo.http import request
import requests
import xml.etree.ElementTree as ET
import urllib.parse

_logger = logging.getLogger(__name__)


class MenuController(http.Controller):

    @http.route('/wechat/check_login', type='http', auth='none', methods=['GET'], csrf=False)
    def wechat_check_login(self, **kw):
        # 检查用户是否已登录
        if request.session.uid:
            _logger.info(f"用户已登录：uid={request.session.uid}")
            # 用户已登录，直接重定向到目标页面
            # 资产看板：estate_dashboard.dashboard
            if kw and kw.get('tgt_page'):
                action_id = request.env.ref(kw.get('tgt_page')).id
                tgt_url = f'/web#action={action_id}'
                return request.redirect(tgt_url)
            else:
                return request.redirect('/web')
        else:
            _logger.info(f"用户未登录")
            # 微信公众号的AppID和AppSecret
            app_id = 'wx5ee57f2a371a203e'
            app_secret = '5e9b2cb2e3511d2f4fede3dde17e4bf7'

            redirect_url = kw.get('tgt_page')
            # 构建微信授权URL
            redirect_uri = urllib.parse.quote_plus(
                f'https://zcgl.491tech.com/wechat/callback?'
                f'app_id={app_id}&app_secret={app_secret}&redirect_url={redirect_url}')

            authorize_url = f'https://open.weixin.qq.com/connect/oauth2/authorize?appid={app_id}&redirect_uri=' \
                            f'{redirect_uri}&response_type=code&scope=snsapi_base&state=STATE#wechat_redirect'

            # 重定向到微信授权页面
            return request.redirect(authorize_url)

    @http.route('/wechat/authorize_callback', type='http', auth='public', methods=['GET'], csrf=False)
    def wechat_callback(self, code=None, state=None, **kw):
        if not code:
            return "Authorization failed: No code provided"

        # 微信公众号的AppID和AppSecret
        app_id = 'wx5ee57f2a371a203e'
        app_secret = '5e9b2cb2e3511d2f4fede3dde17e4bf7'

        # 获取access_token和openid
        token_url = f'https://api.weixin.qq.com/sns/oauth2/access_token?appid={app_id}&secret={app_secret}&code=' \
                    f'{code}&grant_type=authorization_code'
        response = requests.get(token_url)
        data = response.json()

        if 'openid' not in data:
            return "Authorization failed: Unable to get OpenID"

        open_id = data['openid']
        union_id = data['unionid']

        # 检查用户是否已认证
        wx_user = get_wx_user(open_id)

        if wx_user:
            # 已认证用户，直接登录
            request.session.authenticate(request.env.cr.dbname, wx_user.login, wx_user.password)

        else:
            # 未认证用户，跳转至登录页面
            msg = "欢迎使用微信扫码登录系统。由于这是您第一次登录系统，请输入系统用户名和密码点击登录按钮，将系统用户绑定至您的微信。"
            return request.render('wechat.login', {
                'wx_login_msg': msg,
                'open_id': open_id,
                'union_id': union_id,
            })
