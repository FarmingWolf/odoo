# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from math import ceil, floor
from typing import Dict, List

from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError
from . import estate_lease_contract
from odoo import fields, models, api
from ...utils.models.utils import Utils

_logger = logging.getLogger(__name__)


class EstateLeaseContractTurnoverAmtReceived(models.Model):
    _name = "estate.lease.contract.turnover.amt.received"
    _description = "资产租赁合同实收流水"
    _order = "company_id, date_received DESC"

    rental_detail_sub_ids = fields.Many2one(comodel_name='estate.lease.contract.property.rental.detail.sub',
                                            string='合同租金明细', ondelete="cascade")
    deposit_detail_ids = fields.Many2one(comodel_name='estate.lease.contract.property.deposit', string='合同押金明细',
                                         ondelete="cascade")
    water_detail_ids = fields.Many2one(comodel_name='estate.lease.contract.property.fee.water', string='水费明细',
                                       ondelete="cascade")
    electricity_detail_ids = fields.Many2one(comodel_name='estate.lease.contract.property.fee.electricity',
                                             string='电费明细', ondelete="cascade")
    electricity_maintenance_detail_ids = fields.Many2one(
        comodel_name='estate.lease.contract.property.fee.electricity.maintenance', string='电力维护费明细',
        ondelete="cascade")
    maintenance_detail_ids = fields.Many2one(comodel_name='estate.lease.contract.property.fee.maintenance',
                                             string='物业费明细', ondelete="cascade")

    amount_type = fields.Selection(string="实收类别", compute="_compute_received", store=True,
                                   selection=[('contract_rental', '合同租金'), ('contract_deposit', '合同押金'),
                                              ('contract_fee_water', '水费'), ('contract_fee_electricity', '电费'),
                                              ('contract_fee_electricity_maintenance', '电力维护费'),
                                              ('contract_fee_maintenance', '物业费')], )

    amount_receivable = fields.Float(default=0.0, string="本次应收(元)", compute="_compute_received", store=True)
    amount_received = fields.Float(default=0.0, string="本次实收(元)", compute="_compute_received", store=True)
    amount_arrears = fields.Float(default=0.0, string="本次欠缴(元)", compute="_compute_received", store=True)

    date_received = fields.Date(string="实收日期", compute="_compute_received", store=True)

    property_id = fields.Many2one('estate.property', compute="_compute_received", string="资产", ondelete="cascade",
                                  store=True)
    contract_id = fields.Many2one('estate.lease.contract', compute="_compute_received", string="合同", store=True,
                                  ondelete="cascade")

    company_id = fields.Many2one(comodel_name='res.company', compute="_compute_received", store=True,
                                 ondelete="cascade")

    contract_state = fields.Selection(related="contract_id.state", string="合同状态")
    party_a_unit_id = fields.Many2one("estate.lease.contract.party.a.unit", related="contract_id.party_a_unit_id",
                                      ondelete="set null")
    party_a_unit_invisible = fields.Boolean(string="甲方显示与否", related="contract_id.party_a_unit_invisible")
    date_start = fields.Date(string="合同开始日期", related="contract_id.date_start")
    date_rent_start = fields.Date(string="计租开始日期", related="contract_id.date_rent_start")
    date_rent_end = fields.Date(string="计租结束日期", related="contract_id.date_rent_end")

    period_d_start = fields.Date(string="本期开始日", compute="_compute_received", store=True)
    period_d_end = fields.Date(string="本期结束日", compute="_compute_received", store=True)

    renter_id = fields.Many2one('res.partner', string="承租人", related='contract_id.renter_id', store=True,
                                ondelete="set null")

    @api.depends("rental_detail_sub_ids", "deposit_detail_ids", "water_detail_ids", "electricity_detail_ids",
                 "electricity_maintenance_detail_ids", "maintenance_detail_ids", "amount_received", "date_received",
                 "amount_receivable")
    def _compute_received(self):
        for record in self:
            record.amount_type = 'contract_rental'

            if record.rental_detail_sub_ids:
                record.amount_type = 'contract_rental'
                record.amount_receivable = record.rental_detail_sub_ids.rental_receivable_this
                record.amount_received = record.rental_detail_sub_ids.rental_received
                record.date_received = record.rental_detail_sub_ids.date_received
                record.property_id = record.rental_detail_sub_ids.property_id
                record.contract_id = record.rental_detail_sub_ids.contract_id
                record.period_d_start = record.rental_detail_sub_ids.period_date_from
                record.period_d_end = record.rental_detail_sub_ids.period_date_to

            if record.deposit_detail_ids:
                record.amount_type = 'contract_deposit'
                record.amount_receivable = record.deposit_detail_ids.deposit_receivable_this
                record.amount_received = record.deposit_detail_ids.deposit_received
                record.date_received = record.deposit_detail_ids.date_received
                record.property_id = record.deposit_detail_ids.property_id
                record.contract_id = record.deposit_detail_ids.contract_id
                record.period_d_start = record.deposit_detail_ids.date_rent_start
                record.period_d_end = record.deposit_detail_ids.date_rent_end

            if record.water_detail_ids:
                record.amount_type = 'contract_fee_water'
                record.amount_receivable = record.water_detail_ids.water_receivable
                record.amount_received = record.water_detail_ids.water_received
                record.date_received = record.water_detail_ids.date_received
                record.property_id = record.water_detail_ids.property_id
                record.contract_id = record.water_detail_ids.contract_id
                record.period_d_start = record.water_detail_ids.period_d_start
                record.period_d_end = record.water_detail_ids.period_d_end

            if record.electricity_detail_ids:
                record.amount_type = 'contract_fee_electricity'
                record.amount_receivable = record.electricity_detail_ids.electricity_receivable
                record.amount_received = record.electricity_detail_ids.electricity_received
                record.date_received = record.electricity_detail_ids.date_received
                record.property_id = record.electricity_detail_ids.property_id
                record.contract_id = record.electricity_detail_ids.contract_id
                record.period_d_start = record.electricity_detail_ids.period_d_start
                record.period_d_end = record.electricity_detail_ids.period_d_end

            if record.electricity_maintenance_detail_ids:
                record.amount_type = 'contract_fee_electricity_maintenance'
                record.amount_receivable = record.electricity_maintenance_detail_ids.electricity_maintenance_receivable
                record.amount_received = record.electricity_maintenance_detail_ids.electricity_maintenance_received
                record.date_received = record.electricity_maintenance_detail_ids.date_received
                record.property_id = record.electricity_maintenance_detail_ids.property_id
                record.contract_id = record.electricity_maintenance_detail_ids.contract_id
                record.period_d_start = record.electricity_maintenance_detail_ids.period_d_start
                record.period_d_end = record.electricity_maintenance_detail_ids.period_d_end

            if record.maintenance_detail_ids:
                record.amount_type = 'contract_fee_maintenance'
                record.amount_receivable = record.maintenance_detail_ids.maintenance_receivable
                record.amount_received = record.maintenance_detail_ids.maintenance_received
                record.date_received = record.maintenance_detail_ids.date_received
                record.property_id = record.maintenance_detail_ids.property_id
                record.contract_id = record.maintenance_detail_ids.contract_id
                record.period_d_start = record.maintenance_detail_ids.period_d_start
                record.period_d_end = record.maintenance_detail_ids.period_d_end

            record.amount_arrears = record.amount_receivable - record.amount_received
            record.company_id = record.contract_id.company_id

    # 自动拾取每日收款金额流水
    def automatic_daily_pick_turnover_amount_received(self):
        # 合同押金
        _order = "company_id, contract_id, date_received DESC"
        # 最近7天发生变更的数据
        tgt_date = fields.Datetime.now() - relativedelta(days=30)
        _domain = ('write_date', '>=', tgt_date)
        deposit_rcds = self.env["estate.lease.contract.property.deposit"].sudo().search([_domain], order=_order)

        for deposit in deposit_rcds:
            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search([
                ('deposit_detail_ids', '=', deposit.id)])
            if search_rst:
                # 如果存在也只能存在一个，变化的也只可能是金额或日期
                if search_rst[0].amount_receivable != deposit.deposit_receivable_this:
                    search_rst[0].amount_receivable = deposit.deposit_receivable_this
                if search_rst[0].amount_received != deposit.deposit_received:
                    search_rst[0].amount_received = deposit.deposit_received
                if search_rst[0].amount_arrears != search_rst[0].amount_receivable - search_rst[0].amount_received:
                    search_rst[0].amount_arrears = search_rst[0].amount_receivable - search_rst[0].amount_received
                if search_rst[0].date_received != deposit.date_received:
                    search_rst[0].date_received = deposit.date_received
                if search_rst[0].period_d_start != deposit.date_rent_start:
                    search_rst[0].period_d_start = deposit.date_rent_start
                if search_rst[0].period_d_end != deposit.date_rent_end:
                    search_rst[0].period_d_end = deposit.date_rent_end

            else:
                deposit_tgt = {
                    "deposit_detail_ids": deposit.id,

                }
                self.env["estate.lease.contract.turnover.amt.received"].sudo().create(deposit_tgt)

        # 合同租金
        rental_rcds = self.env["estate.lease.contract.property.rental.detail.sub"].sudo().search([_domain], order=_order)
        for rental in rental_rcds:
            if not rental.rental_detail_id.active:
                continue

            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search(
                [('rental_detail_sub_ids', '=', rental.id)])
            if search_rst:
                # 如果存在也只能存在一个，变化的也只可能是金额或日期
                if search_rst[0].amount_receivable != rental.rental_receivable_this:
                    search_rst[0].amount_receivable = rental.rental_receivable_this
                if search_rst[0].amount_received != rental.rental_received:
                    search_rst[0].amount_received = rental.rental_received
                if search_rst[0].amount_arrears != search_rst[0].amount_receivable - search_rst[0].amount_received:
                    search_rst[0].amount_arrears = search_rst[0].amount_receivable - search_rst[0].amount_received
                if search_rst[0].date_received != rental.date_received:
                    search_rst[0].date_received = rental.date_received
                if search_rst[0].period_d_start != rental.period_date_from:
                    search_rst[0].period_d_start = rental.period_date_from
                if search_rst[0].period_d_end != rental.period_date_to:
                    search_rst[0].period_d_end = rental.period_date_to

            else:
                rental_tgt = {
                    "rental_detail_sub_ids": rental.id,

                }
                self.env["estate.lease.contract.turnover.amt.received"].sudo().create(rental_tgt)

        # 水费
        fee_water_rcds = self.env["estate.lease.contract.property.fee.water"].sudo().search([_domain], order=_order)
        for fee_water in fee_water_rcds:
            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search([
                ('water_detail_ids', '=', fee_water.id)])
            if search_rst:
                # 如果存在也只能存在一个，变化的也只可能是金额或日期
                if search_rst[0].amount_receivable != fee_water.water_receivable:
                    search_rst[0].amount_receivable = fee_water.water_receivable
                if search_rst[0].amount_received != fee_water.water_received:
                    search_rst[0].amount_received = fee_water.water_received
                if search_rst[0].amount_arrears != search_rst[0].amount_receivable - search_rst[0].amount_received:
                    search_rst[0].amount_arrears = search_rst[0].amount_receivable - search_rst[0].amount_received
                if search_rst[0].date_received != fee_water.date_received:
                    search_rst[0].date_received = fee_water.date_received
                if search_rst[0].period_d_start != fee_water.period_d_start:
                    search_rst[0].period_d_start = fee_water.period_d_start
                if search_rst[0].period_d_end != fee_water.period_d_end:
                    search_rst[0].period_d_end = fee_water.period_d_end

            else:
                fee_water_tgt = {
                    "water_detail_ids": fee_water.id,
                }
                self.env["estate.lease.contract.turnover.amt.received"].sudo().create(fee_water_tgt)

        # 电费
        fee_electricity_rcds = self.env["estate.lease.contract.property.fee.electricity"].sudo().search([_domain], order=_order)
        for fee_electricity in fee_electricity_rcds:
            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search([
                ('electricity_detail_ids', '=', fee_electricity.id)])
            if search_rst:
                # 如果存在也只能存在一个，变化的也只可能是金额或日期
                if search_rst[0].amount_receivable != fee_electricity.electricity_receivable:
                    search_rst[0].amount_receivable = fee_electricity.electricity_receivable
                if search_rst[0].amount_received != fee_electricity.electricity_received:
                    search_rst[0].amount_received = fee_electricity.electricity_received
                if search_rst[0].amount_arrears != search_rst[0].amount_receivable - search_rst[0].amount_received:
                    search_rst[0].amount_arrears = search_rst[0].amount_receivable - search_rst[0].amount_received
                if search_rst[0].date_received != fee_electricity.date_received:
                    search_rst[0].date_received = fee_electricity.date_received
                if search_rst[0].period_d_start != fee_electricity.period_d_start:
                    search_rst[0].period_d_start = fee_electricity.period_d_start
                if search_rst[0].period_d_end != fee_electricity.period_d_end:
                    search_rst[0].period_d_end = fee_electricity.period_d_end

            else:
                fee_electricity_tgt = {
                    "electricity_detail_ids": fee_electricity.id,
                }
                self.env["estate.lease.contract.turnover.amt.received"].sudo().create(fee_electricity_tgt)

        # 电力维护费
        fee_electricity_maintenance_rcds = self.env["estate.lease.contract.property.fee.electricity.maintenance"].sudo().search([_domain], order=_order)
        for fee_electricity_maintenance in fee_electricity_maintenance_rcds:
            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search([
                ('electricity_maintenance_detail_ids', '=', fee_electricity_maintenance.id)])
            if search_rst:
                # 如果存在也只能存在一个，变化的也只可能是金额或日期
                if search_rst[0].amount_receivable != fee_electricity_maintenance.electricity_maintenance_receivable:
                    search_rst[0].amount_receivable = fee_electricity_maintenance.electricity_maintenance_receivable
                if search_rst[0].amount_received != fee_electricity_maintenance.electricity_maintenance_received:
                    search_rst[0].amount_received = fee_electricity_maintenance.electricity_maintenance_received
                if search_rst[0].amount_arrears != search_rst[0].amount_receivable - search_rst[0].amount_received:
                    search_rst[0].amount_arrears = search_rst[0].amount_receivable - search_rst[0].amount_received
                if search_rst[0].date_received != fee_electricity_maintenance.date_received:
                    search_rst[0].date_received = fee_electricity_maintenance.date_received
                if search_rst[0].period_d_start != fee_electricity_maintenance.period_d_start:
                    search_rst[0].period_d_start = fee_electricity_maintenance.period_d_start
                if search_rst[0].period_d_end != fee_electricity_maintenance.period_d_end:
                    search_rst[0].period_d_end = fee_electricity_maintenance.period_d_end

            else:
                fee_electricity_maintenance_tgt = {
                    "electricity_maintenance_detail_ids": fee_electricity_maintenance.id,
                }
                self.env["estate.lease.contract.turnover.amt.received"].sudo().create(fee_electricity_maintenance_tgt)

        # 物业费
        fee_maintenance_rcds = self.env["estate.lease.contract.property.fee.maintenance"].sudo().search([_domain], order=_order)
        for fee_maintenance in fee_maintenance_rcds:
            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search([
                ('maintenance_detail_ids', '=', fee_maintenance.id)])
            if search_rst:
                # 如果存在也只能存在一个，变化的也只可能是金额或日期
                if search_rst[0].amount_receivable != fee_maintenance.maintenance_receivable:
                    search_rst[0].amount_receivable = fee_maintenance.maintenance_receivable
                if search_rst[0].amount_received != fee_maintenance.maintenance_received:
                    search_rst[0].amount_received = fee_maintenance.maintenance_received
                if search_rst[0].amount_arrears != search_rst[0].amount_receivable - search_rst[0].amount_received:
                    search_rst[0].amount_arrears = search_rst[0].amount_receivable - search_rst[0].amount_received
                if search_rst[0].date_received != fee_maintenance.date_received:
                    search_rst[0].date_received = fee_maintenance.date_received
                if search_rst[0].period_d_start != fee_maintenance.period_d_start:
                    search_rst[0].period_d_start = fee_maintenance.period_d_start
                if search_rst[0].period_d_end != fee_maintenance.period_d_end:
                    search_rst[0].period_d_end = fee_maintenance.period_d_end

            else:
                fee_maintenance_tgt = {
                    "maintenance_detail_ids": fee_maintenance.id,
                }
                self.env["estate.lease.contract.turnover.amt.received"].sudo().create(fee_maintenance_tgt)
