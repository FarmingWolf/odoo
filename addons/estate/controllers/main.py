# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import urllib
from ast import literal_eval

import requests
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


def get_company_lat_lng():

    url = "https://api.map.baidu.com/geocoding/v3/"
    baidu_map_ak = request.env['ir.config_parameter'].sudo().get_param('map_baidu_app_ak')
    company = request.env.user.company_id
    address_city = company.city if company.city else " "
    address_street = company.street if company.street else " "
    address_street2 = company.street2 if company.street2 else " "
    address_company_nm = company.name if company.name else " "

    address = address_city + address_street + address_street2 + address_company_nm
    if not address.strip():
        address = "北京天安门"

    _logger.info(f"公司地址={address}")
    # 请求参数
    params = {
        "address": address,  # 地址
        "output": "json",  # 返回格式
        "ak": baidu_map_ak  # 百度地图AK
    }

    try:
        # 发送HTTP GET请求
        response = requests.get(url, params=params)
        response.raise_for_status()  # 检查请求是否成功

        # 解析返回的JSON数据
        result = response.json()

        _logger.info(f"地址解析result={result}")

        # 检查返回状态
        if result.get("status") == 0:
            location = result["result"]["location"]
            _logger.info(f"返回location={location}")
            return {"longitude": location["lng"], "latitude": location["lat"]}
        else:
            print(f"请求失败，错误信息: {result.get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return None


class EstatePropertyController(Home):

    @http.route(['/estate/baidu_map/get_markers'], type='http', auth="user", website=True, sitemap=True)
    def get_baidu_property_map_markers(self, property_id, **kwargs):
        estate_properties = tools.lazy(lambda: request.env['estate.property'].search([('id', '=', property_id)]))
        property_markers = []
        property_name = ""
        for estate_ad in estate_properties:
            property_name = estate_ad.name
            if estate_ad.latitude and estate_ad.longitude:
                property_markers.append({
                    'latitude': estate_ad.latitude,
                    'longitude': estate_ad.longitude,
                    'name': property_name,
                    'default_company_loc': "0",
                })
        # 如果该资产尚未定位经纬度，那么默认取公司地址
        if not property_markers:
            location = get_company_lat_lng()
            property_markers.append({
                'latitude': location["latitude"],
                'longitude': location["longitude"],
                'name': property_name,
                'default_company_loc': "1",
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

    @http.route(['/estate/baidu_map/get_all_properties'], type='http', auth="user", website=True, sitemap=True)
    def get_baidu_properties_all(self, **kwargs):
        estate_properties = tools.lazy(lambda: request.env['estate.property'].search([]))
        property_markers = []
        for estate_ad in estate_properties:
            property_name = estate_ad.name
            if estate_ad.latitude and estate_ad.longitude:
                property_markers.append({
                    'latitude': estate_ad.latitude,
                    'longitude': estate_ad.longitude,
                    'name': property_name,
                })
        return request.make_response(
            json.dumps(property_markers),  # 将点位信息转换为JSON
            headers=[('Content-Type', 'application/json')]
        )

    @http.route(['/estate/baidu_map/get_company_loc'], type='http', auth="user", website=True, sitemap=True)
    def get_baidu_company_marker(self, **kwargs):
        location = get_company_lat_lng()
        company_marker = [{
            'latitude': location["latitude"],
            'longitude': location["longitude"],
        }]
        return request.make_response(
            json.dumps(company_marker),  # 将点位信息转换为JSON
            headers=[('Content-Type', 'application/json')]
        )
