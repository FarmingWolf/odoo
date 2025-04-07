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
from . import reply
from . import receive
from ...web.controllers.home import Home
# from odoo.addons.web.controllers.home import Home
from openai import OpenAI


_logger = logging.getLogger(__name__)


def deepseek_chat(txt_content,
                  in_base_url="https://api.deepseek.com",
                  tgt_model="deepseek-chat",
                  in_api_key=None):
    try:
        _logger.info(f"in_base_url={in_base_url};tgt_model={tgt_model};in_api_key=?")
        client = OpenAI(api_key=in_api_key, base_url=in_base_url)

        response = client.chat.completions.create(
            model=tgt_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": txt_content},
            ],
            stream=False
        )
        res_content = response.choices[0].message.content
        _logger.info(res_content)
        return res_content

    except Exception as e:
        _logger.error(e)
        return e
