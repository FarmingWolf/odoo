# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.http import request
from odoo.tools.translate import _

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class WechatLogin(models.Model):

    _name = "wechat.login"
    _description = "微信登录模型"

    name = fields.Char(string='微信登录记录')
    access_token = fields.Char(string='access_token')
    expires_in = fields.Char(string='时效（秒）')
    refresh_token = fields.Char(string='refresh_token')
    scope = fields.Char(string='授权作用域')
    open_id = fields.Char(string='open_id')
    union_id = fields.Char(string='union_id')
