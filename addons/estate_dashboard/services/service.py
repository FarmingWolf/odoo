# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


class EstateDashboardService:

    @staticmethod
    def get_statistics_svc(company_id, env):
        latest_property_detail = []
        latest_property_detail_ids = []
        env.cr.execute(
            f"SELECT * FROM estate_lease_contract_property_daily_status "
            f"WHERE status_date = "
            f"( SELECT MAX(status_date) FROM estate_lease_contract_property_daily_status "
            f"WHERE company_id =  {company_id} LIMIT 1 ) "
            f"AND company_id =  {company_id};")
        latest_property_detail_record = env.cr.fetchall()
        for record_tuple in latest_property_detail_record:
            latest_property_detail_ids.append(record_tuple[0])  # 假设id是每条记录的第一个元素

        if latest_property_detail_ids:
            latest_property_detail = env['estate.lease.contract.property.daily.status'].browse(
                latest_property_detail_ids)

        estate_property_quantity = 0
        estate_property_lease_quantity = 0
        estate_property_area_quantity = 0.0
        estate_property_area_lease_quantity = 0.0
        ratio_property_quantity = 1.00
        ratio_property_area_quantity = 1.00

        for record_detail in latest_property_detail:
            estate_property_quantity += 1
            estate_property_area_quantity += float(record_detail.property_rent_area)
            if record_detail.contract_id:
                estate_property_lease_quantity += 1
                estate_property_area_lease_quantity += float(record_detail.property_rent_area)

        if estate_property_quantity != 0:
            ratio_property_quantity = estate_property_lease_quantity / estate_property_quantity

        if estate_property_area_quantity != 0:
            ratio_property_area_quantity = estate_property_area_lease_quantity / estate_property_area_quantity

        _logger.info(f"estate_property_area_quantity=【{estate_property_area_quantity}】")

        return {
            'estate_property_quantity': estate_property_quantity,
            'estate_property_area_quantity': round(estate_property_area_quantity, 2),
            'estate_property_lease_quantity': estate_property_lease_quantity,
            'estate_property_area_lease_quantity': round(estate_property_area_lease_quantity, 2),
            'ratio_property_quantity': round(ratio_property_quantity, 2),
            'ratio_property_area_quantity': round(ratio_property_area_quantity, 2),
            'pie_chart_ratio_property_quantity': {
                '在租间数': estate_property_lease_quantity,
                '空置间数': estate_property_quantity - estate_property_lease_quantity,
            },
            'pie_chart_ratio_property_area_quantity': {
                '在租面积(㎡)': round(estate_property_area_lease_quantity, 2),
                '空置面积(㎡)': round(estate_property_area_quantity - estate_property_area_lease_quantity, 2),
            },
        }