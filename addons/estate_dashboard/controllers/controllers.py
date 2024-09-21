# -*- coding: utf-8 -*-

import logging
import random
from datetime import date

import dateutil.utils

from addons.estate_dashboard.services.service import EstateDashboardService
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class EstateDashboard(http.Controller):
    @http.route('/estate_dashboard/statistics', type='json', auth='user')
    def get_statistics(self, company_id=None):
        """
        返回资产租赁各指标：
        资产总数（房屋间数）、资产总面积（㎡）、在租资产总数（房屋间数）、在租资产总面积（㎡）、在租比率（房屋间数 %）、在租比率（㎡ %）、
        在租空置比图（房屋间数）、在租空置比图（㎡）、
        """
        _logger.info(f"param company_id={company_id}")

        if not company_id:
            company_id = request.env.user.company_id.id
        #
        # latest_property_detail = []
        # latest_property_detail_ids = []
        env = request.env(user=SUPERUSER_ID, su=True)
        obj = EstateDashboardService.get_statistics_svc(company_id, env)
        return obj

    @http.route('/estate_dashboard/statistic_super', type='json', auth='user')
    def get_statistic_super(self):

        allowed_company_ids = request.env.context.get('allowed_company_ids', request.env.companies.ids)
        _logger.info(f"request.env.companies={request.env.companies}")
        _logger.info(f"request.env.companies.ids={request.env.companies.ids}")
        _logger.info(f"allowed_company_ids={allowed_company_ids}")
        allowed_company_data = {}
        for each_company in allowed_company_ids:
            # _logger.info(f"each_company={each_company}")
            # _logger.info(f"each_company is int = {isinstance(each_company, int)}")
            each_company_data = self.get_statistics(each_company)
            # statistics = {
            #     "company_id": each_company,
            #     "company_data": each_company_data,
            # }
            # allowed_company_data[each_company] = statistics
            allowed_company_data[each_company] = each_company_data

        _logger.info(f"allowed_company_data={allowed_company_data}")

        return allowed_company_data
