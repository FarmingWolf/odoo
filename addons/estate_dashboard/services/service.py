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
            latest_property_detail_ids.append(record_tuple[0])  # 每条记录的第一个元素：id

        if latest_property_detail_ids:
            latest_property_detail = env['estate.lease.contract.property.daily.status'].browse(
                latest_property_detail_ids)

        estate_property_quantity = 0
        estate_property_lease_quantity = 0
        estate_property_area_quantity = 0.0
        estate_property_area_lease_quantity = 0.0
        property_area_x_price = 0.0
        property_price_avg = 0.0
        ratio_property_quantity = 1.00
        ratio_property_area_quantity = 1.00
        # 常规计租类型
        conventional_cnt = 0
        conventional_area = 0.0
        conventional_cnt_on_rent = 0
        conventional_area_on_rent = 0.0
        conventional_area_x_price = 0.0
        conventional_price_avg = 0.0
        ratio_conventional_cnt = 1.00
        ratio_conventional_area = 1.00
        # 非常规计租类型（在资产类型中设置计租与否）
        unconventional_cnt = 0
        unconventional_area = 0.0
        unconventional_cnt_on_rent = 0
        unconventional_area_on_rent = 0.0
        unconventional_area_x_price = 0.0
        unconventional_price_avg = 0.0
        ratio_unconventional_cnt = 1.00
        ratio_unconventional_area = 1.00
        # 租金应收实收
        rental_receivable_today = 0.0
        rental_receivable_week = 0.0
        rental_receivable_month = 0.0
        rental_receivable_quarter = 0.0
        rental_receivable_year = 0.0
        rental_received_today = 0.0
        rental_received_week = 0.0
        rental_received_month = 0.0
        rental_received_quarter = 0.0
        rental_received_year = 0.0
        # 押金实收
        rent_deposit_received_today = 0.0
        rent_deposit_received_week = 0.0
        rent_deposit_received_month = 0.0
        rent_deposit_received_quarter = 0.0
        rent_deposit_received_year = 0.0

        for record_detail in latest_property_detail:
            estate_property_quantity += 1
            estate_property_area_quantity += float(record_detail.property_rent_area)
            # 常规计租面积与非常规计租面积（林地等，在资产类型中有设置计租与否）
            if (not record_detail.property_id.property_type_id) or \
                    record_detail.property_id.property_type_id.count_ratio_as_room:
                conventional_cnt += 1
                conventional_area += float(record_detail.property_rent_area)

            if record_detail.contract_id:
                estate_property_lease_quantity += 1
                estate_property_area_lease_quantity += float(record_detail.property_rent_area)
                property_area_x_price += record_detail.property_rent_area * record_detail.property_id.rent_price

                if (not record_detail.property_id.property_type_id) or \
                        record_detail.property_id.property_type_id.count_ratio_as_room:
                    conventional_cnt_on_rent += 1
                    conventional_area_on_rent += float(record_detail.property_rent_area)
                    conventional_area_x_price += record_detail.property_rent_area * record_detail.property_id.rent_price
            # 应收实收
            rental_receivable_today += record_detail.property_rental_receivable_today
            rental_receivable_week += record_detail.property_rental_receivable_week
            rental_receivable_month += record_detail.property_rental_receivable_month
            rental_receivable_quarter += record_detail.property_rental_receivable_quarter
            rental_receivable_year += record_detail.property_rental_receivable_year
            rental_received_today += record_detail.property_rental_received_today
            rental_received_week += record_detail.property_rental_received_week
            rental_received_month += record_detail.property_rental_received_month
            rental_received_quarter += record_detail.property_rental_received_quarter
            rental_received_year += record_detail.property_rental_received_year
            rent_deposit_received_today += record_detail.property_rent_deposit_received_today
            rent_deposit_received_week += record_detail.property_rent_deposit_received_week
            rent_deposit_received_month += record_detail.property_rent_deposit_received_month
            rent_deposit_received_quarter += record_detail.property_rent_deposit_received_quarter
            rent_deposit_received_year += record_detail.property_rent_deposit_received_year

        if estate_property_quantity != 0:
            ratio_property_quantity = estate_property_lease_quantity / estate_property_quantity

        if estate_property_area_quantity != 0:
            ratio_property_area_quantity = estate_property_area_lease_quantity / estate_property_area_quantity

        if estate_property_area_lease_quantity != 0:
            property_price_avg = property_area_x_price / estate_property_area_lease_quantity

        if conventional_cnt != 0:
            ratio_conventional_cnt = conventional_cnt_on_rent / conventional_cnt

        if conventional_area != 0:
            ratio_conventional_area = conventional_area_on_rent / conventional_area

        if conventional_area_on_rent != 0:
            conventional_price_avg = conventional_area_x_price / conventional_area_on_rent

        unconventional_cnt = estate_property_quantity - conventional_cnt
        unconventional_area = round(estate_property_area_quantity - conventional_area, 2)
        unconventional_cnt_on_rent = estate_property_lease_quantity - conventional_cnt_on_rent
        unconventional_area_on_rent = estate_property_area_lease_quantity - conventional_area_on_rent
        unconventional_area_x_price = property_area_x_price - conventional_area_x_price
        if unconventional_cnt != 0:
            ratio_unconventional_cnt = unconventional_cnt_on_rent / unconventional_cnt

        if unconventional_area != 0:
            ratio_unconventional_area = unconventional_area_on_rent / unconventional_area

        if unconventional_area_on_rent != 0:
            unconventional_price_avg = unconventional_area_x_price / unconventional_area_on_rent

        _logger.info(f"estate_property_area_quantity=【{estate_property_area_quantity}】")

        return {
            'estate_property_quantity': estate_property_quantity,
            'estate_property_area_quantity': round(estate_property_area_quantity, 2),
            'estate_property_lease_quantity': estate_property_lease_quantity,
            'estate_property_area_lease_quantity': round(estate_property_area_lease_quantity, 2),
            'ratio_property_quantity': round(ratio_property_quantity, 2),
            'ratio_property_area_quantity': round(ratio_property_area_quantity, 2),
            'property_price_avg': round(property_price_avg, 2),

            'pie_chart_ratio_property_quantity': {
                '在租数量': estate_property_lease_quantity,
                '空置数量': estate_property_quantity - estate_property_lease_quantity,
            },
            'pie_chart_ratio_property_area_quantity': {
                '在租面积(㎡)': round(estate_property_area_lease_quantity, 2),
                '空置面积(㎡)': round(estate_property_area_quantity - estate_property_area_lease_quantity, 2),
            },
            'latest_property_detail': latest_property_detail,

            'conventional_cnt': conventional_cnt,
            'conventional_area': round(conventional_area, 2),
            'conventional_cnt_on_rent': conventional_cnt_on_rent,
            'conventional_area_on_rent': round(conventional_area_on_rent, 2),
            'conventional_price_avg': round(conventional_price_avg, 2),
            'ratio_conventional_cnt': round(ratio_conventional_cnt, 2),
            'ratio_conventional_area': round(ratio_conventional_area, 2),

            'unconventional_cnt': unconventional_cnt,
            'unconventional_area': unconventional_area,
            'unconventional_cnt_on_rent': unconventional_cnt_on_rent,
            'unconventional_area_on_rent': unconventional_area_on_rent,
            'unconventional_price_avg': round(unconventional_price_avg, 2),
            'ratio_unconventional_cnt': ratio_unconventional_cnt,
            'ratio_unconventional_area': ratio_unconventional_area,

            'pie_chart_ratio_conventional_quantity': {
                '在租间数': conventional_cnt_on_rent,
                '空置间数': conventional_cnt - conventional_cnt_on_rent,
            },
            'pie_chart_ratio_conventional_area_quantity': {
                '在租面积(㎡)': round(conventional_area_on_rent, 2),
                '空置面积(㎡)': round(conventional_area - conventional_area_on_rent, 2),
            },

            'pie_chart_ratio_unconventional_quantity': {
                '在租地块': estate_property_lease_quantity - conventional_cnt_on_rent,
                '空置地块':
                    estate_property_quantity - estate_property_lease_quantity -
                    conventional_cnt + conventional_cnt_on_rent,
            },
            'pie_chart_ratio_unconventional_area_quantity': {
                '在租面积(㎡)': round(estate_property_area_lease_quantity - conventional_area_on_rent, 2),
                '空置面积(㎡)':
                    round(estate_property_area_quantity - estate_property_area_lease_quantity -
                          conventional_area + conventional_area_on_rent, 2),
            },
            # 应收实收
            'rental_receivable_today': round(rental_receivable_today, 2),
            'rental_receivable_week': round(rental_receivable_week, 2),
            'rental_receivable_month': round(rental_receivable_month, 2),
            'rental_receivable_quarter': round(rental_receivable_quarter, 2),
            'rental_receivable_year': round(rental_receivable_year, 2),
            'rental_received_today': round(rental_received_today, 2),
            'rental_received_week': round(rental_received_week, 2),
            'rental_received_month': round(rental_received_month, 2),
            'rental_received_quarter': round(rental_received_quarter, 2),
            'rental_received_year': round(rental_received_year, 2),
            'rent_deposit_received_today': round(rent_deposit_received_today, 2),
            'rent_deposit_received_week': round(rent_deposit_received_week, 2),
            'rent_deposit_received_month': round(rent_deposit_received_month, 2),
            'rent_deposit_received_quarter': round(rent_deposit_received_quarter, 2),
            'rent_deposit_received_year': round(rent_deposit_received_year, 2),
        }
