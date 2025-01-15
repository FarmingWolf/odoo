# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import urllib
from ast import literal_eval
from dateutil.relativedelta import relativedelta

import base64
import json
import logging
import math
import werkzeug

from odoo import fields, http, tools, _
from odoo.http import request, Response
from ...web.controllers.home import Home

_logger = logging.getLogger(__name__)


class EstatePropertyController(Home):

    @http.route(['/estate/baidu_map/get_markers'], type='http', auth="user", website=True, sitemap=True)
    def get_baidu_property_map_markers(self, property_id, **kwargs):
        estate_properties = tools.lazy(lambda: request.env['estate.property'].search([('id', '=', property_id)]))
        property_markers = []
        for estate_ad in estate_properties:
            if estate_ad.latitude and estate_ad.longitude:
                property_markers.append({
                    'latitude': estate_ad.latitude,
                    'longitude': estate_ad.longitude,
                    'name': estate_ad.name,
                })
        _logger.info(f"property_markers={property_markers}")
        return request.make_response(
            json.dumps(property_markers),  # 将点位信息转换为JSON
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/estate/update_property_location', type='json', auth='user')
    def update_property_location(self, property_id, latitude, longitude):
        # 更新记录的位置
        tgt_property = request.env['estate.property'].browse(property_id)

        _logger.info(f"更新位置，经度={longitude},纬度={latitude}")
        tgt_property.write({
            'latitude': latitude,
            'longitude': longitude,
        })
        return {'success': True}
