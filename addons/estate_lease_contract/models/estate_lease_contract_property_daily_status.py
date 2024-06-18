# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import date, timedelta
from typing import Dict, List

from odoo import fields, models, api

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

    contract_id = fields.Many2one('estate.lease.contract', string="在租合同")
    contract_state = fields.Char(string='合同状态')
    contract_date_sign = fields.Date(string="合同签订日期")
    contract_date_start = fields.Date(string="合同开始日期")
    contract_date_rent_start = fields.Date(string="计租开始日期")
    contract_date_rent_end = fields.Date(string="计租结束日期")

    cal_date_s = fields.Date(string="重计算开始日期")
    cal_date_e = fields.Date(string="重计算结束日期")

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

    def automatic_daily_calc_status(self):
        _logger.info("开始做成资产租赁状态每日数据")
        # 每日JOB从数据库里记录的最新一天开始往后按天计算
        latest_date = self.env['estate.lease.contract.property.daily.status'].search([], order='status_date DESC',
                                                                                     limit=1)
        # 如果数据库中有数据，则以其为基准，计算其后一日
        if latest_date:
            if latest_date[0].status_date:
                record_status_date = latest_date[0].status_date + timedelta(days=1)
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
        while record_status_date < record_status_date_end:
            # 先删除重计算目标日期数据
            self_domain = ['|', ('status_date', '=', record_status_date), ('property_id', '=', False)]
            search_cnt = self.env['estate.lease.contract.property.daily.status'].search_count(self_domain)
            if search_cnt:
                _logger.info("即将删除{0}条记录".format(search_cnt))
                self.env['estate.lease.contract.property.daily.status'].search(self_domain).unlink()

            property_ids = self.env['estate.property'].search([])
            for each_property in property_ids:
                record_name = f"{record_status_date}-{each_property.name}"
                record_property_id = each_property
                # 先把资产状态设置为空
                record_property_state = None
                record_property_date_availability = each_property.date_availability

                # 查询该日期对应的有效合同
                contract_domain = [('property_ids', '=', each_property.id), ('active', '=', True),
                                   ('state', '=', 'released'), ('date_rent_start', '<=', record_status_date),
                                   ('date_rent_end', '>=', record_status_date), ]
                property_contract = self.env['estate.lease.contract'].search(contract_domain, order='id DESC',
                                                                             limit=1)
                # 默认没有合同，则先设置每个字段为空
                record_contract_id = None
                record_contract_state = None
                record_contract_date_sign = None
                record_contract_date_start = None
                record_contract_date_rent_start = None
                record_contract_date_rent_end = None

                for contract in property_contract:
                    # 有合同时再设置其资产状态
                    record_property_state = dict(each_property._fields['state'].selection).get(each_property.state)
                    record_contract_id = contract
                    record_contract_state = dict(contract._fields['state'].selection).get(contract.state)
                    record_contract_date_sign = contract.date_sign
                    record_contract_date_start = contract.date_start
                    record_contract_date_rent_start = contract.date_rent_start
                    record_contract_date_rent_end = contract.date_rent_end

                if record_contract_id:
                    record_contract_id_id = record_contract_id.id
                else:
                    record_contract_id_id = None

                self.env['estate.lease.contract.property.daily.status'].create({
                    'name': record_name,
                    'status_date': record_status_date,
                    'property_id': record_property_id.id,
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
                })
                int_cnt += 1

            record_status_date = record_status_date + timedelta(days=1)
        _logger.info(
            "资产租赁状态{0}至{1}数据做成{2}条。".format(record_status_date_s, record_status_date_end - timedelta(days=1), int_cnt))
