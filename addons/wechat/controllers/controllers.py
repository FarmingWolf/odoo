# -*- coding: utf-8 -*-
import base64
import binascii
import hashlib
import logging
import random
import traceback

import requests

import odoo
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home  # 即使有提示import错误也要这么写。。。启动服务和运行时没错

_logger = logging.getLogger(__name__)

SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang', 'signup_email'}


def get_wx_user(open_id):
    _logger.info("checking is_wx_user_exists")
    env = request.env
    wechat_user = env['wechat.users'].sudo().search([('open_id', '=', open_id)], limit=1)
    _logger.info(f"wechat_user={wechat_user}")

    return wechat_user


def get_wx_user_by_union_id(union_id):
    _logger.info("checking is_wx_user_exists by union_id")
    env = request.env
    wechat_user = env['wechat.users'].sudo().search([('union_id', '=', union_id)], limit=1)
    _logger.info(f"wechat_user={wechat_user}")

    return wechat_user


def pwd_encoded(param):
    pwd_rdm1 = random.randint(1, 2)
    pwd_rdm11 = random.randint(2, 3)
    byte_str = param.encode('utf-8')
    for i in range(pwd_rdm1):
        pwd_rdm2 = random.randint(2, 3)
        while pwd_rdm2 == pwd_rdm11:
            pwd_rdm2 = random.randint(2, 3)
        pwd_rdm11 = pwd_rdm2
        for ii in range(pwd_rdm2):
            if i == min(range(pwd_rdm1)) and ii == min(range(pwd_rdm2)):
                b_e = base64.b64encode(byte_str)
            else:
                b_e = base64.b64encode(a_e)
            a_e = binascii.hexlify(b_e)

        a_e = str(pwd_rdm2).encode('utf-8') + a_e

    a_e = str(pwd_rdm1).encode('utf-8') + a_e

    return a_e


def pwd_decoded(param):
    rdm_num_1 = int(param.decode('utf-8')[0])
    rdm_a_e = param[1: len(param)]
    for i in range(rdm_num_1):
        if i == min(range(rdm_num_1)):
            rdm_num_i = int(rdm_a_e.decode('utf-8')[0])
            rdm_a_e_i = rdm_a_e[1: len(rdm_a_e)]
        else:
            rdm_num_i = int(b_e_dec.decode('utf-8')[0])
            rdm_a_e_i = b_e_dec[1: len(b_e_dec)]

        for ii in range(rdm_num_i):
            if ii == min(range(rdm_num_i)):
                a_e_dec = binascii.unhexlify(rdm_a_e_i)
            else:
                a_e_dec = binascii.unhexlify(b_e_dec)
            b_e_dec = base64.b64decode(a_e_dec)
    return b_e_dec.decode('utf-8')


def wechat_user_silent_login(in_self, in_wechat_user, in_redirect_url):

    try:
        request.params['login'] = in_wechat_user.res_user_id.login
        request.params['password'] = pwd_decoded(in_wechat_user.password.encode('utf-8'))
        uid = request.session.authenticate(request.db, request.params['login'],
                                           request.params['password'])
        request.params['login_success'] = True
        return request.redirect(in_self.super()._login_redirect(uid, redirect=in_redirect_url))
    except Exception as ex:
        msg = f"系统提示错误：{ex}{ex.with_traceback}。" \
              "看起来，您最近更新了登陆密码，请输入用户名和最新密码点击登录按钮。"
        _logger.info(f"sys error:{ex}", exc_info=True)
        traceback.print_exc()
        # 重定向到登录页
        return request.render('wechat.login', {
            'wx_login_msg': msg,
            'open_id': in_wechat_user.open_id,
            'union_id': in_wechat_user.union_id,
        })


class WechatHandle(Home):

    @http.route('/wechat/handle', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def get(self, **kwargs):
        """用于验证请求是否来自微信公众号服务器"""
        try:
            _logger.info(kwargs)

            data = kwargs
            if len(data) == 0:
                return "hello, welcome!"

            signature = data.get('signature')
            timestamp = data.get('timestamp')
            nonce = data.get('nonce')
            echo_str = data.get('echostr')
            # 每个新公众号需要单独设置wechat_handle_token
            tk_from_config = request.env['ir.config_parameter'].sudo().get_param('wechat_handle_token')
            token = tk_from_config if tk_from_config else '491tech4wechat9token1'

            in_list = [token, timestamp, nonce]
            in_list.sort()
            _logger.info(f'in_list={in_list}')
            sha1 = hashlib.sha1()

            for item in in_list:
                sha1.update(item.encode('utf-8'))

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

        app_id_from_kw = kw.get('app_id')
        app_secret_from_kw = kw.get('app_secret')
        redirect_url_from_kw = kw.get('redirect_url')

        app_id = 'wx2dadd8272b906e46'
        redirect_url = None

        if app_id_from_kw:
            app_id = app_id_from_kw
        app_secret = "f5638550687027ce9f07016ace9e391f"
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

                    # 重定向到登录页
                    return request.render('wechat.login', {
                        'wx_login_msg': msg,
                        'open_id': open_id,
                        'union_id': union_id,
                    })

                # 不是第一次登录，则用绑定的账号登录成功
                for wechat_user in wx_user:

                    request.session['callback_data_open_id'] = open_id
                    request.session['callback_data_union_id'] = union_id
                    # 刷新access_token有效期
                    refresh_tk_url = f"https://api.weixin.qq.com/sns/oauth2/refresh_token?appid=" \
                                     f"{app_id}&grant_type=refresh_token&refresh_token={refresh_token}"

                    refresh_tk_res = requests.get(refresh_tk_url)
                    refresh_tk_data = refresh_tk_res.json()

                    login_result = wechat_user_silent_login(self, wechat_user, redirect_url)

                    return login_result
            else:
                # 错误处理
                error_message = res_data.get('errmsg', '未知错误')
                return f"登录失败：{error_message}"

        except Exception as e:
            return f"微信access_token请求失败：{str(e)}"

    """继承web.controllers.home覆盖web_login方法"""
    @http.route('/web/login', type='http', auth="none")
    def web_login(self, *args, **kw):

        response = super().web_login(*args, **kw)
        _logger.info(f"response.is_qweb={response.is_qweb}")
        _logger.info(f"response.status_code={response.status_code}")

        # 绑定微信用户
        if not response.is_qweb and response.status_code == 303:
            if 'callback_data_open_id' in request.session:
                wx_name = request.session['callback_data_open_id']
                open_id = request.session['callback_data_open_id']
                union_id = request.session['callback_data_union_id']

                tgt_wx_usr = get_wx_user(open_id)
                str_pwd = pwd_encoded(request.params['password'])

                env = request.env
                res_user_id = env.user.id
                if tgt_wx_usr:
                    _logger.info(f"更新用户{res_user_id}的密码")
                    tgt_wx_usr.password = str_pwd
                else:
                    _logger.info(f"创建用户{res_user_id}的微信open_id：{open_id}")
                    env['wechat.users'].sudo().create({
                        'name': wx_name,
                        'open_id': open_id,
                        'union_id': union_id,
                        'res_user_id': res_user_id,
                        'password': str_pwd,
                    })

        return response
