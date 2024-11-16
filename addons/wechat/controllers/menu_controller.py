import json
import logging

from .controllers import get_wx_user, pwd_decoded, get_wx_user_by_union_id, wechat_user_silent_login
from odoo import http
from odoo.http import request
import requests
import xml.etree.ElementTree as ET
import urllib.parse

from ...web.controllers.home import Home
# from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)


def create_wechat_menu(access_token, app_id):
    menu_def_url = f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}"
    post_data_str = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_menu')
    post_data = json.loads(post_data_str)
    try:
        _logger.info(f"menu_def_url={menu_def_url}")
        post_data_json = json.dumps(post_data, ensure_ascii=False).encode('utf-8')
        response = requests.post(menu_def_url, data=post_data_json, headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            _logger.info(f"微信菜单生成OK")
        else:
            _logger.error(f"微信菜单生成NG")

        _logger.info(f"wechat menu：{response.text}")

    except Exception as e:
        _logger.error(f"微信菜单生成失败：{str(e)}")


def get_wx_stable_token(in_app_id, in_app_secret):
    stable_token_url = "https://api.weixin.qq.com/cgi-bin/stable_token"
    token_post_data = {
        "grant_type": "client_credential",
        "appid": in_app_id,
        "secret": in_app_secret
    }
    token_res = requests.post(stable_token_url, json=token_post_data)
    _logger.info(f"token_res={token_res}")
    token_ret_data = token_res.json()
    _logger.info(f"token_ret_data={token_ret_data}")
    return token_ret_data


class MenuController(Home):

    @http.route('/wechat/check_login', type='http', auth='none', methods=['GET'], csrf=False, sitemap=False)
    def wechat_check_login(self, **kw):
        """本方法专用于微信公众号菜单：资产看板"""
        tgt_url = "/web"
        if kw and kw.get('tgt_page'):
            action_id = request.env.ref(kw.get('tgt_page')).id
            tgt_url = f'/web#action={action_id}'

        _logger.info(f"tgt_url={tgt_url}")
        # 检查用户是否已登录
        if request.session.uid:
            _logger.info(f"用户已登录：uid={request.session.uid}")
            # 用户已登录，直接重定向到目标页面：资产看板estate_dashboard.dashboard
            return request.redirect(tgt_url)

        else:
            _logger.info(f"用户未登录")
            # 微信公众号的AppID和AppSecret
            app_id = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_id')
            app_secret = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_secret')

            redirect_url = urllib.parse.quote_plus(tgt_url)
            # 构建微信授权URL
            redirect_uri = urllib.parse.quote_plus(
                f'https://zcgl.491tech.com/wechat/authorize_callback?'
                f'app_id={app_id}&app_secret={app_secret}&redirect_url={redirect_url}')

            authorize_url = f'https://open.weixin.qq.com/connect/oauth2/authorize?' \
                            f'appid={app_id}&redirect_uri={redirect_uri}&' \
                            f'response_type=code&scope=snsapi_userinfo&state=STATE#wechat_redirect'

            _logger.info(f"authorize_url={authorize_url}")

            # 获取openid/unionid并回调至
            try:
                return request.redirect(authorize_url, local=False)

            except Exception as e:
                _logger.error(f"微信静默登录失败：{str(e)}")
                return request.redirect(tgt_url)

    @http.route('/wechat/create_wx_menu', type='http', auth='none', methods=['GET'], csrf=False, sitemap=False)
    def create_wx_menu(self, **kw):

        app_id = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_id')
        app_secret = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_secret')

        app_id_from_kw = kw.get('app_id')
        app_secret_from_kw = kw.get('app_secret')

        if app_id_from_kw:
            app_id = app_id_from_kw
        if app_secret_from_kw:
            app_secret = app_secret_from_kw

        # 获取stable_token
        token_ret_data = get_wx_stable_token(app_id, app_secret)
        # 创建自定义菜单
        create_wechat_menu(token_ret_data["access_token"], app_id)
