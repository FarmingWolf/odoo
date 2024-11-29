# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from math import ceil, floor
from typing import Dict, List

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
                                            string='租金收缴明细', ondelete="cascade")
    deposit_detail_ids = fields.Many2one(comodel_name='estate.lease.contract.property.deposit', string='押金收缴明细',
                                         ondelete="cascade")

    amount_type = fields.Selection(string="实收类别", compute="_compute_received", store=True,
                                   selection=[('contract_rental', '合同租金'),
                                              ('contract_deposit', '合同押金')], )

    amount_received = fields.Float(default=0.0, string="本次实收(元)", compute="_compute_received", store=True)

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
    renter_id = fields.Many2one('res.partner', string="承租人", related='contract_id.renter_id', store=True,
                                ondelete="set null")

    @api.depends("rental_detail_sub_ids", "deposit_detail_ids")
    def _compute_received(self):
        for record in self:
            record.amount_type = 'contract_rental'

            if record.rental_detail_sub_ids and record.rental_detail_sub_ids.rental_received >= 0.01:
                record.amount_type = 'contract_rental'
                record.amount_received = record.rental_detail_sub_ids.rental_received
                record.date_received = record.rental_detail_sub_ids.date_received
                record.property_id = record.rental_detail_sub_ids.property_id
                record.contract_id = record.rental_detail_sub_ids.contract_id

            if record.deposit_detail_ids and record.deposit_detail_ids.deposit_received >= 0.01:
                record.amount_type = 'contract_deposit'
                record.amount_received = record.deposit_detail_ids.deposit_received
                record.date_received = record.deposit_detail_ids.date_received
                record.property_id = record.deposit_detail_ids.property_id
                record.contract_id = record.deposit_detail_ids.contract_id

            record.company_id = record.contract_id.company_id


    # 自动拾取每日收款金额流水
    def automatic_daily_pick_turnover_amount_received(self):
        # 合同押金
        _order = "company_id, contract_id, date_received DESC"
        deposit_rcds = self.env["estate.lease.contract.property.deposit"].sudo().search([], order=_order)

        for deposit in deposit_rcds:
            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search_count([
                ('deposit_detail_ids', '=', deposit.id)])
            if search_rst > 0:
                continue

            deposit_tgt = {
                "deposit_detail_ids": deposit.id,

            }
            self.env["estate.lease.contract.turnover.amt.received"].sudo().create(deposit_tgt)

        # 合同租金
        rental_rcds = self.env["estate.lease.contract.property.rental.detail.sub"].sudo().search([], order=_order)
        for rental in rental_rcds:
            search_rst = self.env["estate.lease.contract.turnover.amt.received"].sudo().search_count(
                [('rental_detail_sub_ids', '=', rental.id)])
            if search_rst > 0:
                continue

            rental_tgt = {
                "rental_detail_sub_ids": rental.id,

            }
            self.env["estate.lease.contract.turnover.amt.received"].sudo().create(rental_tgt)
