# -*- coding: utf-8 -*-

import logging
import random

from addons.estate_dashboard.services.service import compute_company_statistics
from odoo import http, fields
from odoo.http import request
from odoo.tools import date_utils

_logger = logging.getLogger(__name__)


def get_12_months_end_dates_around_today():
    """
    返回以当前日期为基准的前后12个月的月末日期列表（共25个月）
    格式: ['2023-01-31', '2023-02-28', ..., '2025-01-31']
    """
    today = fields.Date.today()
    months = []

    # 获取当前月份的第一天
    first_day_of_current_month = date_utils.start_of(today, 'month')

    # 向前12个月
    for i in range(12, 0, -1):
        month_start = date_utils.subtract(first_day_of_current_month, months=i)
        month_end = date_utils.end_of(month_start, 'month')
        months.append(month_end)

    # 添加当前日期
    if today.day > 2:
        current_date = date_utils.subtract(today, days=1)
        months.append(current_date)

    return [date for date in months]


class EstateBigScreen(http.Controller):
    @http.route('/estate_big_screen/statistics', type='json', auth='user')
    def get_line_chart_data(self):
        if not request.env.user.has_group('estate_big_screen.estate_group_big_screen'):
            _logger.error(f"用户{request.env.user.id}:{request.env.user.name}没有大屏权限")
            return {}

        date_lst = get_12_months_end_dates_around_today()
        # 以当前日期为基准，查询过去12个月的租金单价、面积出租率、租金实收、租金应收
        tgt_model = 'estate.lease.contract.property.daily.status'
        tgt_domain = [('status_date', 'in', date_lst), ('company_id', '=', request.env.user.company_id.id)]
        dataset = request.env[tgt_model].search(tgt_domain, order="status_date asc")

        average_price_lst = []
        rent_ratio_lst = []
        rental_received_lst = []
        rental_receivable_lst = []

        len_lst = len(date_lst)
        i = 1
        for tgt_dt in date_lst:
            company_statistics = compute_company_statistics(dataset.search([('status_date', '=', tgt_dt)]))

            dt = f"{tgt_dt.month}-{tgt_dt.day}"
            if i != len_lst or company_statistics['property_price_avg'] != 0:
                average_price_lst.append({'y': company_statistics['property_price_avg'], 'x': dt})

            if i != len_lst or company_statistics['ratio_conventional_area'] != 0:
                rent_ratio_lst.append({'y': company_statistics['ratio_conventional_area'], 'x': dt})

            if i != len_lst or company_statistics['rental_received_month'] != 0:
                rental_received_lst.append({'y': company_statistics['rental_received_month'] / 10000, 'x': dt})

            if i != len_lst or company_statistics['rental_receivable_month'] != 0:
                rental_receivable_lst.append({'y': company_statistics['rental_receivable_month'] / 10000, 'x': dt})

            i += 1

        return {
            'average_price_lst': average_price_lst,
            'rent_ratio_lst': rent_ratio_lst,
            'rental_received_lst': rental_received_lst,
            'rental_receivable_lst': rental_receivable_lst,
        }

    @http.route('/estate_big_screen/get_out_of_rent_properties', type='json', auth='user')
    def get_out_of_rent_properties(self):
        if not request.env.user.has_group('estate_big_screen.estate_group_big_screen'):
            _logger.error(f"用户{request.env.user.id}:{request.env.user.name}没有大屏权限")
            return []
        _logger.info("开始获取空置资产")
        tgt_model = 'estate.property'
        tgt_domain = [('active', '=', True), '|', ('state', '!=', 'sold'), ('state', '=', False)]
        dataset = request.env[tgt_model].search(tgt_domain, order="date_availability ASC")
        rtn_lst = []
        for record in dataset:
            # 过滤掉不计入租金的资产类型
            if record.property_type_id and not record.property_type_id.count_ratio_as_room:
                continue

            rtn_lst.append(
                {record.id: {
                    '资产名称': record.name,
                    '面积': record.rent_area,
                    '本次空置天数': record.out_of_rent_days,
                    '资产类型': record.property_type_id.name if record.property_type_id else '',
                }})

        _logger.info(f"一共{len(rtn_lst)}条空置资产")
        return rtn_lst

    @http.route('/estate_big_screen/get_company_nm_4_big_screen', type='json', auth='user')
    def get_company_nm_4_big_screen(self):

        company_id = request.env.user.company_id.id
        company_nm = request.env.user.company_id.name
        if request.env.user.company_id.company_nm_4_big_screen:
            company_nm = request.env.user.company_id.company_nm_4_big_screen

        _logger.info(f"company_nm={company_nm}")
        return {company_id: company_nm}

    @http.route('/estate_big_screen/get_park_vehicles_registered_today', type='json', auth='user')
    def get_park_vehicles_registered_today(self):

        vehicles_cnt = request.env['park.vehicle.assignation.log'].get_vehicles_cnt(request.env.user.company_id.id,
                                                                                    request.env)
        company_vehicle_cnt = 0
        for vehicle_cnt in vehicles_cnt:
            if request.env.user.company_id.id == vehicle_cnt[0].id:
                company_vehicle_cnt = vehicle_cnt[1]
                break
        return company_vehicle_cnt

    @http.route('/estate_big_screen/get_parking_spaces', type='json', auth='user')
    def get_parking_spaces(self):

        spaces = request.env['parking.space'].get_parking_space_cnt(request.env.user.company_id.id, request.env, False)
        spaces_reserved = request.env['parking.space'].get_parking_space_cnt(request.env.user.company_id.id,
                                                                             request.env, True)
        spots_bound, vehicle_bound = request.env['parking.space'].get_parking_space_reserved_bound(request.env.user.company_id.id,
                                                                                                   request.env)

        return {"parking_spaces_cnt": spaces,
                "parking_spaces_reserved_cnt": spaces_reserved,
                "parking_spaces_reserved_bound_cnt": spots_bound,
                "parking_spaces_reserved_bound_vehicles_cnt": vehicle_bound}
