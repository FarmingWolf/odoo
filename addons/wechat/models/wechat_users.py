# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.http import request
from odoo.tools.translate import _

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class WechatUsers(models.Model):

    _name = "wechat.users"
    _description = "微信用户模型"

    name = fields.Char(string='微信用户')
    open_id = fields.Char(string='open_id')
    union_id = fields.Char(string='union_id')
    res_user_id = fields.Many2one('res.users', string='系统内用户')
    password = fields.Char(string='密码')
