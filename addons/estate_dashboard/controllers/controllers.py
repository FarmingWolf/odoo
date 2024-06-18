# -*- coding: utf-8 -*-

import logging
import random

from odoo import http
from odoo.http import request

logger = logging.getLogger(__name__)


class EstateDashboard(http.Controller):
    @http.route('/estate_dashboard/statistics', type='json', auth='user')
    def get_statistics(self):
        """
        返回资产租赁各指标：
        资产总数（房屋间数）、资产总面积（㎡）、在租资产总数（房屋间数）、在租资产总面积（㎡）、在租比率（房屋间数 %）、在租比率（㎡ %）、
        在租空置比图（房屋间数）、在租空置比图（㎡）、
        """

        return {
            'estate_property_quantity': random.randint(4, 12),
            'estate_property_area_quantity': random.randint(4, 123),
            'estate_property_lease_quantity': random.randint(10, 200),
            'estate_property_area_lease_quantity': random.randint(0, 50),
            'ratio_property_quantity': random.randint(0, 50),
            'ratio_property_area_quantity': random.randint(0, 50),
            'pie_chart_ratio_property_quantity': {
                '在租间数': random.randint(0, 150),
                '空置间数': random.randint(0, 150),
            },
            'pie_chart_ratio_property_area_quantity': {
                '在租面积(㎡)': random.randint(0, 150),
                '空置面积(㎡)': random.randint(0, 150),
            },
        }
