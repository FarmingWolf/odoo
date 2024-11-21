# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import date, timedelta
from typing import Dict, List

from odoo import fields, models, api, SUPERUSER_ID
from odoo.cli.scaffold import env
from odoo.tools import end_of, start_of

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyDailyStatus(models.Model):
    _name = "estate.lease.contract.property.daily.status"
    _description = "资产出租每日状态"
    _order = "status_date DESC, contract_id ASC, property_id ASC"

    name = fields.Char(string="资产出租状态明细")
    status_date = fields.Date(string="状态日期")
    property_id = fields.Many2one('estate.property', string="资产（房屋）")
    property_state = fields.Char(string='资产状态')
    property_date_availability = fields.Date(string="可租日期")
    property_building_area = fields.Float(string="建筑面积")
    property_rent_area = fields.Float(string="计租面积")

    contract_id = fields.Many2one('estate.lease.contract', string="在租合同")
    contract_state = fields.Char(string='合同状态')
    contract_date_sign = fields.Date(string="合同签订日期")
    contract_date_start = fields.Date(string="合同开始日期")
    contract_date_rent_start = fields.Date(string="计租开始日期")
    contract_date_rent_end = fields.Date(string="计租结束日期")

    cal_date_s = fields.Date(string="重计算开始日期")
    cal_date_e = fields.Date(string="重计算结束日期")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    property_rental_receivable_today = fields.Float(string="本日应收")
    property_rental_receivable_week = fields.Float(string="本周应收")
    property_rental_receivable_month = fields.Float(string="本月应收")
    property_rental_receivable_quarter = fields.Float(string="本季应收")
    property_rental_receivable_year = fields.Float(string="本年应收")
    property_rental_received_today = fields.Float(string="本日实收")
    property_rental_received_week = fields.Float(string="本周实收")
    property_rental_received_month = fields.Float(string="本月实收")
    property_rental_received_quarter = fields.Float(string="本季实收")
    property_rental_received_year = fields.Float(string="本年实收")

    @api.model
    def create(self, vals):
        for record in self:
            if record.status_date:
                if record.status_date == date.today():
                    return
            else:
                return

            if record.property_id:
                if not record.property_id.id:
                    return

        return super().create(vals)

    def calc_record_rental_info(self, in_contract_id, in_property_id, in_date, in_rental_info):

        details = self.env["estate.lease.contract.property.rental.detail"].search(
            [('contract_id', '=', in_contract_id), ('property_id', '=', in_property_id), ('active', '=', True)])

        detail_subs = self.env["estate.lease.contract.property.rental.detail.sub"].search(
            [('rental_detail_id', 'in', details.ids)])

        for rental_detail in details:
            if rental_detail.date_payment == in_date:
                in_rental_info['property_rental_receivable_today'] += rental_detail.rental_receivable
            if end_of(rental_detail.date_payment, 'week') == end_of(in_date, 'week'):
                in_rental_info['property_rental_receivable_week'] += rental_detail.rental_receivable
            if end_of(rental_detail.date_payment, 'month') == end_of(in_date, 'month'):
                in_rental_info['property_rental_receivable_month'] += rental_detail.rental_receivable
            if end_of(rental_detail.date_payment, 'quarter') == end_of(in_date, 'quarter'):
                in_rental_info['property_rental_receivable_quarter'] += rental_detail.rental_receivable
            if end_of(rental_detail.date_payment, 'year') == end_of(in_date, 'year'):
                in_rental_info['property_rental_receivable_year'] += rental_detail.rental_receivable

        for detail_sub in detail_subs:
            if detail_sub.date_received == in_date:
                in_rental_info['property_rental_received_today'] += detail_sub.rental_received
            if end_of(detail_sub.date_received, 'week') == end_of(in_date, 'week'):
                in_rental_info['property_rental_received_week'] += detail_sub.rental_received
            if end_of(detail_sub.date_received, 'month') == end_of(in_date, 'month'):
                in_rental_info['property_rental_received_month'] += detail_sub.rental_received
            if end_of(detail_sub.date_received, 'quarter') == end_of(in_date, 'quarter'):
                in_rental_info['property_rental_received_quarter'] += detail_sub.rental_received
            if end_of(detail_sub.date_received, 'year') == end_of(in_date, 'year'):
                in_rental_info['property_rental_received_year'] += detail_sub.rental_received

        return in_rental_info

    def automatic_daily_calc_status(self):
        _logger.info("开始做成资产租赁状态每日数据")
        if 'is_from_page_click' in self.env.context and self.env.context.get('is_from_page_click') is True:
            self.env.cr.execute(f'SELECT DISTINCT company_id FROM estate_property WHERE company_id = '
                                f'{self.env.user.company_id.id}')
        else:
            self = self.with_user(SUPERUSER_ID)
            self.env.cr.execute(f'SELECT DISTINCT company_id FROM estate_property')

        property_companies = set(self.env.cr.fetchall())

        for company_id in property_companies:
            # 每日JOB从数据库里记录的最新一天开始往后按天计算
            domain = ('company_id', '=', company_id[0])
            latest_date = self.env['estate.lease.contract.property.daily.status'].search([domain],
                                                                                         order='status_date DESC',
                                                                                         limit=1)
            # 如果数据库中有数据，则重新计算其最大日期数据，计算至date.today()
            if latest_date:
                if latest_date[0].status_date:
                    record_status_date = latest_date[0].status_date
                else:
                    record_status_date = date.today() - timedelta(days=1)
            else:
                record_status_date = date.today() - timedelta(days=1)

            # 默认计算到当前日期前一天
            record_status_date_end = date.today()

            # 如果是来自form视图的刷新按钮，则以cal_date_s和cal_date_e为计算对象日期范围
            for self_record in self:
                _logger.info("cal_date_s={0},cal_date_e={1}".format(self_record.cal_date_s, self_record.cal_date_e))
                if self_record.cal_date_s:
                    record_status_date = self_record.cal_date_s
                    record_status_date_end = record_status_date + timedelta(days=1)

                if self_record.cal_date_e:
                    if self_record.cal_date_e >= record_status_date_end:
                        record_status_date_end = self_record.cal_date_e + timedelta(days=1)

            record_status_date_s = record_status_date
            _logger.info("计算开始日期{0},计算结束日期{1}".format(record_status_date_s, record_status_date_end))
            int_cnt = 0

            property_ids = self.env['estate.property'].search([domain])
            while record_status_date < record_status_date_end:
                # 先删除重计算目标日期数据
                self_domain = ['&', domain,
                               '|', ('status_date', '=', record_status_date), ('property_id', '=', False)]
                search_cnt = self.env['estate.lease.contract.property.daily.status'].search_count(self_domain)
                if search_cnt:
                    _logger.info("即将删除{0}条记录".format(search_cnt))
                    self.env['estate.lease.contract.property.daily.status'].search(self_domain).unlink()

                for each_property in property_ids:
                    record_name = f"{record_status_date}-{each_property.name}"
                    record_property_id = each_property
                    # 先把资产状态设置为空
                    record_property_state = None
                    record_property_date_availability = each_property.date_availability
                    record_property_building_area = each_property.building_area
                    record_property_rent_area = each_property.rent_area

                    # 查询该日期对应的有效合同
                    contract_domain = [('property_ids', '=', each_property.id), ('active', '=', True),
                                       ('terminated', '=', False), ('state', 'in', ['to_be_released', 'released']),
                                       ('date_rent_end', '>=', record_status_date), ]
                    property_contract = self.env['estate.lease.contract'].search(contract_domain,
                                                                                 order='date_rent_end DESC')
                    # 默认没有合同，则先设置每个字段为空
                    record_contract_id = None
                    record_contract_state = None
                    record_contract_date_sign = None
                    record_contract_date_start = None
                    record_contract_date_rent_start = None
                    record_contract_date_rent_end = None

                    rental_info = {
                        "property_rental_receivable_today": 0,
                        "property_rental_receivable_week": 0,
                        "property_rental_receivable_month": 0,
                        "property_rental_receivable_quarter": 0,
                        "property_rental_receivable_year": 0,
                        "property_rental_received_today": 0,
                        "property_rental_received_week": 0,
                        "property_rental_received_month": 0,
                        "property_rental_received_quarter": 0,
                        "property_rental_received_year": 0,
                    }
                    record_rental_info = rental_info
                    # 合同有效时才设置其资产已租状态,业务上、理论上和逻辑上时间段不会重叠
                    for contract in property_contract:
                        if (contract.property_state_by_date_sign and
                            contract.date_sign <= record_status_date) or \
                                (contract.property_state_by_date_start and
                                 contract.date_start <= record_status_date) or \
                                (contract.property_state_by_date_rent_start and
                                 contract.date_rent_start <= record_status_date):

                            record_property_state = dict(
                                each_property._fields['state'].selection).get(each_property.state)
                            record_contract_id = contract
                            record_contract_state = dict(contract._fields['state'].selection).get(contract.state)
                            record_contract_date_sign = contract.date_sign
                            record_contract_date_start = contract.date_start
                            record_contract_date_rent_start = contract.date_rent_start
                            record_contract_date_rent_end = contract.date_rent_end

                            record_rental_info = self.calc_record_rental_info(contract.id, each_property.id,
                                                                              record_status_date, rental_info)

                    if record_contract_id:
                        record_contract_id_id = record_contract_id.id
                    else:
                        record_contract_id_id = None

                    # 对于当年失效的合同，也要统计其当年已收租金
                    contract_invalid = [('property_ids', '=', each_property.id), ('active', '=', True),
                                        ('state', '=', 'invalid'),
                                        ('date_rent_end', '<', record_status_date),
                                        ('date_rent_end', '>=', start_of(record_status_date, 'year')), ]
                    property_contract_invalid = self.env['estate.lease.contract'].search(contract_invalid,
                                                                                         order='date_rent_end DESC')
                    for contract in property_contract_invalid:
                        record_rental_info = self.calc_record_rental_info(contract.id, each_property.id,
                                                                          record_status_date, record_rental_info)

                    self.env['estate.lease.contract.property.daily.status'].create({
                        'name': record_name,
                        'status_date': record_status_date,
                        'property_id': record_property_id.id,
                        'property_building_area': record_property_building_area,
                        'property_rent_area': record_property_rent_area,
                        'property_state': record_property_state,
                        'property_date_availability': record_property_date_availability,
                        'contract_id': record_contract_id_id,
                        'contract_state': record_contract_state,
                        'contract_date_sign': record_contract_date_sign,
                        'contract_date_start': record_contract_date_start,
                        'contract_date_rent_start': record_contract_date_rent_start,
                        'contract_date_rent_end': record_contract_date_rent_end,
                        'cal_date_s': record_status_date_s,
                        'cal_date_e': record_status_date_end,
                        'company_id': company_id[0],
                        "property_rental_receivable_today": record_rental_info['property_rental_receivable_today'],
                        "property_rental_receivable_week": record_rental_info['property_rental_receivable_week'],
                        "property_rental_receivable_month": record_rental_info['property_rental_receivable_month'],
                        "property_rental_receivable_quarter": record_rental_info['property_rental_receivable_quarter'],
                        "property_rental_receivable_year": record_rental_info['property_rental_receivable_year'],
                        "property_rental_received_today": record_rental_info['property_rental_received_today'],
                        "property_rental_received_week": record_rental_info['property_rental_received_week'],
                        "property_rental_received_month": record_rental_info['property_rental_received_month'],
                        "property_rental_received_quarter": record_rental_info['property_rental_received_quarter'],
                        "property_rental_received_year": record_rental_info['property_rental_received_year'],
                    })
                    int_cnt += 1

                record_status_date = record_status_date + timedelta(days=1)
            _logger.info(f"公司{company_id[0]},"
                         f"{record_status_date_s}至{record_status_date_end - timedelta(days=1)}数据做成{int_cnt}条。")
