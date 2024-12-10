# -*- coding: utf-8 -*-
import base64
import binascii
import hashlib
import logging
import random
import traceback
import urllib
import urllib.parse

import requests

import odoo
from .controllers import get_wx_user, pwd_decoded, get_wx_user_by_union_id, wechat_user_silent_login
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)


class WechatQRCodeHandle(Home):

    @http.route('/wechat/callback', type='http', auth='public', methods=['GET', 'POST'], csrf=False, sitemap=False)
    def wechat_callback(self, **kw):
        _logger.info("entering WechatQRCodeHandle wechat/callback")
        # 这个方法用于处理微信回调
        # 从回调中获取code，然后通过code换取access_token和openid
        # 最终根据openid找到对应的Odoo用户并登录
        code = kw.get('code')

        app_id_from_kw = kw.get('app_id')
        app_secret_from_kw = kw.get('app_secret')
        redirect_url_from_kw = kw.get('redirect_url')

        app_id = request.env['ir.config_parameter'].sudo().get_param('wechat_open_plat_app_id')
        redirect_url = None

        if app_id_from_kw:
            app_id = app_id_from_kw
        app_secret = request.env['ir.config_parameter'].sudo().get_param('wechat_open_plat_app_secret')
        if app_secret_from_kw:
            app_secret = app_secret_from_kw
        if redirect_url_from_kw:
            redirect_url = redirect_url_from_kw

        access_tk_url = f"https://api.weixin.qq.com/sns/oauth2/access_token?appid=" \
                        f"{app_id}&secret={app_secret}&code={code}&grant_type=authorization_code"
        try:
            res = requests.get(access_tk_url)
            res_data = res.json()
            if 'access_token' in res_data:
                # 成功获取access_token
                access_token = res_data['access_token']
                expires_in = res_data['expires_in']
                refresh_token = res_data['refresh_token']
                open_id = res_data['openid']
                scope = res_data['scope']
                union_id = res_data['unionid']

                # 在这里可以使用access_token来获取用户信息或其他操作
                # 示例：保存access_token和其他相关信息到数据库
                env = request.env
                env['wechat.login'].sudo().create({
                    'name': open_id,
                    'access_token': access_token,
                    'expires_in': expires_in,
                    'refresh_token': refresh_token,
                    'open_id': open_id,
                    'scope': scope,
                    'union_id': union_id,
                })

                wx_user = get_wx_user(open_id)
                # 第一次扫码登陆，输入UID/PWD绑定微信
                if not wx_user:
                    _logger.info(f"第一次登陆：{open_id}")
                    # 要求用户输入系统UID/PWD
                    msg = "欢迎使用微信扫码登录系统。由于这是您第一次登录系统，请输入系统用户名和密码点击登录按钮，将系统用户绑定至您的微信。"
                    request.session['callback_data_open_id'] = open_id
                    request.session['callback_data_union_id'] = union_id
                    # 刷新access_token有效期
                    refresh_tk_url = f"https://api.weixin.qq.com/sns/oauth2/refresh_token?appid=" \
                                     f"{app_id}&grant_type=refresh_token&refresh_token={refresh_token}"

                    refresh_tk_res = requests.get(refresh_tk_url)
                    refresh_tk_data = refresh_tk_res.json()
                    _logger.info(f"refresh_tk_data={refresh_tk_data}")

                    # 重定向到登录页
                    return request.redirect_query("/web/login", query={"wx_login_msg": msg})
                    # return request.render('wechat.login', {
                    #     'wx_login_msg': msg,
                    #     'open_id': open_id,
                    #     'union_id': union_id,
                    # })

                # 不是第一次登录，则用绑定的账号登录成功
                for wechat_user in wx_user:

                    request.session['callback_data_open_id'] = open_id
                    request.session['callback_data_union_id'] = union_id
                    # 刷新access_token有效期
                    refresh_tk_url = f"https://api.weixin.qq.com/sns/oauth2/refresh_token?appid=" \
                                     f"{app_id}&grant_type=refresh_token&refresh_token={refresh_token}"

                    refresh_tk_res = requests.get(refresh_tk_url)
                    refresh_tk_data = refresh_tk_res.json()

                    try:
                        request.params['login'] = wechat_user.res_user_id.login
                        request.params['password'] = pwd_decoded(wechat_user.password.encode('utf-8'))
                        uid = request.session.authenticate(request.db, request.params['login'],
                                                           request.params['password'])
                        request.params['login_success'] = True
                        return request.redirect(self._login_redirect(uid, redirect=redirect_url))
                    except Exception as ex:
                        msg = f"系统提示错误：{ex}{ex.with_traceback}。" \
                              "看起来，您最近更新了登陆密码，请输入用户名和最新密码点击登录按钮。"
                        _logger.info(f"sys error:{ex}", exc_info=True)
                        traceback.print_exc()
                        # 重定向到登录页
                        return request.redirect_query("/web/login", query={"wx_login_msg": msg})

                        # return request.render('wechat.login', {
                        #     'wx_login_msg': msg,
                        #     'open_id': open_id,
                        #     'union_id': union_id,
                        # })

            else:
                # 错误处理
                error_message = res_data.get('errmsg', '未知错误')
                return f"登录失败：{error_message}"

        except Exception as e:
            return f"微信access_token请求失败：{str(e)}"

    @http.route('/wechat/authorize_callback', type='http', auth='none', methods=['GET'], csrf=False, sitemap=False)
    def wechat_authorize_callback(self, code=None, state=None, **kw):
        """
        todo 需要调查from ...web.controllers.home import Home这种写法不认识本路由，却认识/wechat/check_login
        而from odoo.addons.web.controllers.home import Home才识得本路由，
        但是也不能改成from odoo.addons.web.controllers.home import Home，因为改后self没有super()也没有_login_redirect方法
        """
        _logger.info(f"收到微信回调请求: code={code}, state={state}, kw={kw}")
        if not code:
            _logger.error("参数code错误")
            return "Authorization failed: No code provided……"

        # 微信公众号的AppID和AppSecret
        app_id = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_id')
        app_secret = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_secret')
        redirect_url = "/web"

        app_id_from_kw = kw.get('app_id')
        app_secret_from_kw = kw.get('app_secret')
        redirect_url_from_kw = kw.get('redirect_url')

        if app_id_from_kw:
            app_id = app_id_from_kw
        if app_secret_from_kw:
            app_secret = app_secret_from_kw
        if redirect_url_from_kw:
            redirect_url = redirect_url_from_kw

        _logger.info(f"app_id={app_id};app_secret={app_secret};redirect_url={redirect_url}")

        # 获取access_token和openid
        token_url = f'https://api.weixin.qq.com/sns/oauth2/access_token?appid={app_id}&secret={app_secret}&code=' \
                    f'{code}&grant_type=authorization_code'
        response = requests.get(token_url)
        data = response.json()
        _logger.info(f"获取access_token和openid响应: {data}")

        if 'openid' not in data:
            _logger.error("获取openid错误")
            return "Authorization failed: Unable to get OpenID"

        open_id = data['openid']
        union_id = data['unionid']
        _logger.info(f"来自微信的回调：open_id={open_id};union_id={union_id}")

        # 检查用户是否已认证
        wx_user = get_wx_user_by_union_id(union_id)
        _logger.info(f"wx_user={wx_user}")

        if not wx_user:
            request.session['callback_data_open_id'] = open_id
            request.session['callback_data_union_id'] = union_id
            # 未认证用户，跳转至登录页面
            msg = "欢迎使用微信扫码登录系统。由于这是您第一次登录系统，请输入系统用户名和密码点击登录按钮，将系统用户绑定至您的微信。"
            # return request.render('wechat.login', {
            #     'wx_login_msg': msg,
            #     'open_id': open_id,
            #     'union_id': union_id,
            # })
            return request.redirect_query("/web/login", query={"wx_login_msg": msg})

        for we_chat_user in wx_user:
            # 已认证用户，直接登录

            login_result = wechat_user_silent_login(self, we_chat_user, redirect_url)

            return login_result
