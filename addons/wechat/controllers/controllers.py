# -*- coding: utf-8 -*-
import base64
import binascii
import hashlib
import logging
import random
import re
import traceback

import requests

import odoo
from odoo import http
from odoo.http import request
from odoo.tools import json
from . import reply
from . import receive
from .deepseek_controllers import deepseek_chat
from ...web.controllers.home import Home
# from odoo.addons.web.controllers.home import Home
from .api_middleware import validate_token

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
        return request.redirect(in_self._login_redirect(uid, redirect=in_redirect_url))
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


def get_wechat_token():

    app_id = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_id')
    app_secret = request.env['ir.config_parameter'].sudo().get_param('wechat_service_app_secret')
    token_data = get_wx_stable_token(app_id, app_secret)
    token = token_data["access_token"]

    return token


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


def get_hashcode(in_timestamp, in_nonce):
    # 每个新公众号需要单独设置wechat_handle_token
    tk_from_config = request.env['ir.config_parameter'].sudo().get_param('wechat_handle_token')
    token = tk_from_config if tk_from_config else '491tech4wechat9token1'

    in_list = [token, in_timestamp, in_nonce]
    in_list.sort()
    _logger.info(f'in_list={in_list}')
    sha1 = hashlib.sha1()

    for item in in_list:
        sha1.update(item.encode('utf-8'))

    hashcode = sha1.hexdigest()
    return hashcode


def get_deepseek_base():
    deepseek_config_str = request.env['ir.config_parameter'].sudo().get_param('wechat_deepseek_config')
    _logger.info(f"deepseek_config_str={deepseek_config_str}")
    config_json = json.loads(deepseek_config_str)
    return config_json


def _get_business_self(msc_content, to_user):
    """
    todo
    判断提问者是否具有系统权限后，根据问题匹配系统可接受的问题，如果没有匹配上，那么返回用户标准问题列表，引导用户输入标准问题序号，
    然后根据用户的标准问题序号，处理并返回答案
    """
    return "功能持续开发中，敬请期待！"


class WechatHandle(Home):

    @http.route('/wechat/handle', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def get(self, **kwargs):
        try:
            _logger.info(f"/wechat/handle kwargs={kwargs}")
            in_data = kwargs
            """用于验证请求是否来自微信公众号服务器"""
            if request.httprequest.method == 'GET':
                if len(in_data) == 0:
                    return "hello, welcome!"

                signature = in_data.get('signature')
                timestamp = in_data.get('timestamp')
                nonce = in_data.get('nonce')
                echo_str = in_data.get('echostr')
                # 服务器有效性验证
                if signature and timestamp and nonce:

                    hashcode = get_hashcode(timestamp, nonce)
                    _logger.info(f"handle/GET func: hashcode={hashcode}, signature={signature} ")
                    if echo_str:
                        if hashcode == signature:
                            return echo_str
                        else:
                            return "hello, welcome!!"
                    else:
                        msg = "此时应有不同于业务处理和有效性验证的业务……暂时什么也不做，返回success"
                        _logger.info(msg)
                        return "success"

                return "hello, welcome!!!"

            elif request.httprequest.method == 'POST':
                signature = in_data.get('signature')
                timestamp = in_data.get('timestamp')
                nonce = in_data.get('nonce')
                if signature and timestamp and nonce:
                    hashcode = get_hashcode(timestamp, nonce)
                    if hashcode != signature:
                        return "hello, welcome!!!"
                    # 消息和事件处理
                    web_data = request.httprequest.data.decode('utf-8')
                    _logger.info(f"web_data:{web_data}")
                    if web_data:

                        if len(web_data) == 0:
                            return "success"

                        rec_msg = receive.parse_xml(web_data)
                        _logger.info(f"rec_msg in post:{rec_msg}")

                        if isinstance(rec_msg, receive.Msg):
                            to_user = rec_msg.FromUserName
                            from_user = rec_msg.ToUserName

                            if rec_msg.MsgType == 'text':
                                _logger.info(f"rec_msg.Content={rec_msg.Content}")
                                msc_content = rec_msg.Content.decode('utf-8')
                                _logger.info(f"rec_msg.Content.decode={msc_content}")
                                """ 对接deepseek
                                deepseek_config_json = get_deepseek_base()
                                ret_deepseek = deepseek_chat(msc_content,
                                                             deepseek_config_json["in_base_url"],
                                                             deepseek_config_json["tgt_model"],
                                                             deepseek_config_json["in_api_key"])

                                if not ret_deepseek:
                                    ret_deepseek = "您好！公众号交互功能研发中，将陆续上线，敬请期待！"

                                ret_deepseek = ret_deepseek.replace("\n\n", "\n")
                                ret_deepseek = ret_deepseek.replace("**", "")
                                ret_deepseek = ret_deepseek.replace("- ", "")
                                ret_deepseek = ret_deepseek[0: 800]
                                _logger.info(f"处理后的返回值={ret_deepseek}")
                                reply_msg = reply.TextMsg(to_user, from_user, ret_deepseek)
                                """
                                ret_business_self = _get_business_self(msc_content, to_user)
                                reply_msg = reply.TextMsg(to_user, from_user, ret_business_self)
                                return reply_msg.send()
                            elif rec_msg.MsgType == 'voice':
                                # 语音转文字
                                wec_token = get_wechat_token()
                                _logger.info(f"rec_msg.voice_id={rec_msg.MediaId};wec_token={wec_token}")
                                voice_url_s = f"https://api.weixin.qq.com/cgi-bin/media/voice/addvoicetorecofortext?" \
                                              f"access_token={wec_token}&format=&voice_id={rec_msg.MediaId}&lang=zh_CN"

                                ret_res = requests.post(voice_url_s)
                                _logger.info(f"ret_res={ret_res}")
                                res_txt = ret_res.json()
                                txt_content = res_txt["errmsg"]
                                _logger.info(f"errmsg={txt_content}")

                                reply_txt = "您好！公众号语音交互功能研发中，将陆续上线，敬请期待！"
                                if txt_content == "ok":
                                    res_url = f"https://api.weixin.qq.com/cgi-bin/media/voice/queryrecoresultfortext?" \
                                              f"access_token={wec_token}&voice_id={rec_msg.MediaId}&lang=zh_CN"

                                    ret_res = requests.post(res_url)
                                    res_txt = ret_res.json()
                                    txt_content = res_txt["result"]
                                    _logger.info(f"语音转换文字={txt_content}")
                                    deepseek_config_json = get_deepseek_base()
                                    ret_deepseek = deepseek_chat(txt_content,
                                                                 deepseek_config_json["in_base_url"],
                                                                 deepseek_config_json["tgt_model"],
                                                                 deepseek_config_json["in_api_key"])

                                    if ret_deepseek:
                                        ret_deepseek = ret_deepseek.replace("\n\n", "\n")
                                        ret_deepseek = ret_deepseek.replace("**", "")
                                        ret_deepseek = ret_deepseek.replace("- ", "")
                                        reply_txt = ret_deepseek[0: 800]
                                        _logger.info(f"处理后的返回值={reply_txt}")

                                else:
                                    reply_txt = "您好！目前公众号仅识别中文普通话，其他语言版本将陆续上线，敬请期待！"

                                reply_msg = reply.TextMsg(to_user, from_user, reply_txt)
                                return reply_msg.send()

                            elif rec_msg.MsgType == 'event':
                                if rec_msg.Event == 'subscribe':
                                    content = "您好！欢迎关注491科技！北京四九一科技公司坐落于北京朝阳491园区。" \
                                              "我们是一支充满激情朝气磅礴的团队！我们的愿景是试图通过构建一个具有颠覆意义的软件系统、" \
                                              "一个具有颠覆意义的产品！以此提升每一家中小企业的产品品质， " \
                                              "来解决各位在商业活动中遇到的诸多经营问题！您可以随时文字或语音提问，我将努力解答^_^"
                                    reply_msg = reply.TextMsg(to_user, from_user, content)
                                    return reply_msg.send()

                                _logger.info(f"rec_msg.MsgType=event, rec_msg.Event={rec_msg.Event}")

                            _logger.info(f"其他情况待处理:rec_msg.MsgType={rec_msg.MsgType}")
                            return "success"
                        else:
                            _logger.info("暂且不处理")
                            return "success"

                    else:
                        return "hello, welcome!!!!"
                else:
                    return "hello, welcome!!!!!"

            else:
                return "hello, welcome!!!!!!"

        except Exception as e:
            _logger.error(e)
            return e

    @http.route('/wechat/qr-code', type='http', auth='none', methods=['GET', 'POST'], csrf=False, sitemap=False)
    def get_qr_code(self, **kw):
        # 这个方法应该返回一个包含二维码的响应
        # 你可以使用微信提供的API来生成二维码并返回
        # 这里仅作示例，你需要根据实际情况实现
        return request.render('wechat.qr_code', {})

    @http.route('/wechat/callback', type='http', auth='none', methods=['GET', 'POST'], csrf=False, sitemap=False)
    def wechat_callback(self, **kw):
        _logger.info("entering controllers wechat/callback")
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
        # todo 确认可否给args传递tgt_url
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

    # 添加小程序登录接口
    @http.route('/wechat/miniprogram/login', type='json', auth='none', methods=['POST'], csrf=False)
    def miniprogram_login(self, **kw):
        """
        小程序登录接口
        参数:
            code: 小程序登录code
            app_id: 小程序appid (可选，如不提供则使用系统配置)
            app_secret: 小程序secret (可选，如不提供则使用系统配置)
        """
        try:
            _logger.info(f"小程序登录请求: {kw}")
            code = kw.get('code')
            if not code:
                return {'success': False, 'message': '缺少code参数'}
                
            # 获取小程序配置
            app_id = kw.get('app_id') or request.env['ir.config_parameter'].sudo().get_param('wechat_little_pgm_app_id')
            app_secret = kw.get('app_secret') or request.env['ir.config_parameter'].sudo().get_param('wechat_little_pgm_app_secret')
            
            if not app_id or not app_secret:
                return {'success': False, 'message': '未配置小程序参数'}
                
            # 请求微信接口获取openid和session_key
            url = f"https://api.weixin.qq.com/sns/jscode2session?appid={app_id}&secret={app_secret}&js_code={code}&grant_type=authorization_code"
            res = requests.get(url)
            res_data = res.json()
            
            _logger.info(f"微信小程序登录返回: {res_data}")
            
            if 'openid' not in res_data:
                return {'success': False, 'message': res_data.get('errmsg', '获取openid失败')}
                
            open_id = res_data['openid']
            union_id = res_data.get('unionid', '')  # 如果用户有授权，可能会返回unionid
            session_key = res_data.get('session_key', '')
            
            # 查找用户
            wx_user = get_wx_user(open_id)
            if not wx_user and union_id:
                # 如果有unionid但没找到openid，尝试通过unionid查找
                wx_user = get_wx_user_by_union_id(union_id)
                
            # 生成自定义登录态token
            token = hashlib.md5((open_id + str(random.random())).encode('utf-8')).hexdigest()
            
            # 保存会话信息
            env = request.env
            session_data = {
                'token': token,
                'open_id': open_id,
                'session_key': session_key,
                'union_id': union_id,
                'create_time': odoo.fields.Datetime.now(),
                'expire_time': odoo.fields.Datetime.to_string(
                    odoo.fields.Datetime.from_string(odoo.fields.Datetime.now()) + 
                    odoo.fields.timedelta(days=7)  # 设置7天有效期
                ),
            }
            
            # 存储会话信息
            env['wechat.miniprogram.session'].sudo().create(session_data)
            
            result = {
                'success': True,
                'token': token,
                'is_registered': bool(wx_user),
                'user_info': {}
            }
            
            # 如果用户已注册，返回用户信息
            if wx_user:
                user = wx_user.res_user_id
                result['user_info'] = {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email,
                }
                
            return result
            
        except Exception as e:
            _logger.error(f"小程序登录异常: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'服务器错误: {str(e)}'}
            
    @http.route('/wechat/miniprogram/register', type='json', auth='none', methods=['POST'], csrf=False)
    def miniprogram_register(self, **kw):
        """
        小程序用户注册/绑定接口
        参数:
            token: 登录接口返回的token
            login: 用户名
            password: 密码
        """
        try:
            token = kw.get('token')
            login = kw.get('login')
            password = kw.get('password')
            
            if not all([token, login, password]):
                return {'success': False, 'message': '参数不完整'}
                
            # 验证token有效性
            env = request.env
            session = env['wechat.miniprogram.session'].sudo().search([
                ('token', '=', token),
                ('expire_time', '>=', odoo.fields.Datetime.now())
            ], limit=1)
            
            if not session:
                return {'success': False, 'message': '无效的token或已过期'}
                
            open_id = session.open_id
            union_id = session.union_id
            
            # 验证用户名密码
            try:
                uid = request.session.authenticate(request.db, login, password)
                if not uid:
                    return {'success': False, 'message': '用户名或密码错误'}
            except Exception as e:
                return {'success': False, 'message': f'登录验证失败: {str(e)}'}
                
            # 获取用户
            user = env['res.users'].sudo().browse(uid)
            
            # 检查是否已绑定微信
            wx_user = get_wx_user(open_id)
            if not wx_user:
                # 创建新的微信用户绑定
                str_pwd = pwd_encoded(password)
                env['wechat.users'].sudo().create({
                    'name': user.name,
                    'open_id': open_id,
                    'union_id': union_id,
                    'res_user_id': user.id,
                    'password': str_pwd,
                })
                
            return {
                'success': True,
                'message': '绑定成功',
                'user_info': {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email,
                }
            }
            
        except Exception as e:
            _logger.error(f"小程序注册异常: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'服务器错误: {str(e)}'}
            
    @http.route('/wechat/miniprogram/check_token', type='json', auth='none', methods=['POST'], csrf=False)
    def check_token(self, **kw):
        """
        验证token有效性
        参数:
            token: 登录接口返回的token
        """
        try:
            token = kw.get('token')
            if not token:
                return {'success': False, 'message': '缺少token参数'}
                
            env = request.env
            session = env['wechat.miniprogram.session'].sudo().search([
                ('token', '=', token),
                ('expire_time', '>=', odoo.fields.Datetime.now())
            ], limit=1)
            
            if not session:
                return {'success': False, 'message': '无效的token或已过期'}
                
            open_id = session.open_id
            wx_user = get_wx_user(open_id)
            
            if not wx_user:
                return {'success': True, 'is_registered': False}
                
            user = wx_user.res_user_id
            return {
                'success': True,
                'is_registered': True,
                'user_info': {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email,
                }
            }
            
        except Exception as e:
            _logger.error(f"验证token异常: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'服务器错误: {str(e)}'}

    # 添加token验证中间件
    def _validate_miniprogram_token(self, token):
        """验证小程序token有效性"""
        if not token:
            return None
            
        env = request.env
        session = env['wechat.miniprogram.session'].sudo().search([
            ('token', '=', token),
            ('expire_time', '>=', odoo.fields.Datetime.now())
        ], limit=1)
        
        if not session:
            return None
            
        open_id = session.open_id
        wx_user = get_wx_user(open_id)
        
        if not wx_user:
            return None
            
        return wx_user

    @http.route('/wechat/miniprogram/api/user_info', type='json', auth='none', methods=['POST'], csrf=False)
    @validate_token
    def get_user_info(self, **kw):
        """
        获取用户信息接口（需要token验证）
        """
        try:
            # 通过中间件验证，wx_user已经在kwargs中
            wx_user = kw.get('wx_user')
            user = wx_user.res_user_id
            
            return {
                'success': True,
                'user_info': {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email,
                }
            }
            
        except Exception as e:
            _logger.error(f"获取用户信息异常: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'服务器错误: {str(e)}'}
            
    @http.route('/wechat/miniprogram/api/update_profile', type='json', auth='none', methods=['POST'], csrf=False)
    @validate_token
    def update_profile(self, **kw):
        """
        更新用户信息接口（需要token验证）
        """
        try:
            # 通过中间件验证，wx_user已经在kwargs中
            wx_user = kw.get('wx_user')
            user = wx_user.res_user_id
            
            # 获取要更新的字段
            update_data = {}
            if 'name' in kw:
                update_data['name'] = kw.get('name')
            if 'email' in kw:
                update_data['email'] = kw.get('email')
                
            if update_data:
                user.write(update_data)
                
            return {
                'success': True,
                'message': '更新成功',
                'user_info': {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email,
                }
            }
            
        except Exception as e:
            _logger.error(f"更新用户信息异常: {str(e)}", exc_info=True)
            return {'success': False, 'message': f'服务器错误: {str(e)}'}
