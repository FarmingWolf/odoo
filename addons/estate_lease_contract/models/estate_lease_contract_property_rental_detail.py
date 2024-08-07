# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from typing import Dict, List
from . import estate_lease_contract
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyRentalDetail(models.Model):
    _name = "estate.lease.contract.property.rental.detail"
    _description = "资产租赁合同租金明细"
    _order = "property_id, period_date_from"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    contract_id = fields.Many2one('estate.lease.contract', string="合同")
    property_id = fields.Many2one('estate.property', string="租赁标的")
    rental_amount = fields.Float(default=0.0, string="本期租金(元)", tracking=True)
    rental_amount_zh = fields.Char(string="本期租金(元)大写")
    rental_receivable = fields.Float(default=0.0, string="本期应收(元)", compute="_get_default_rental_receivable",
                                     readonly=False, store=True, digits=(12, 2), tracking=True)
    rental_received = fields.Float(default=0.0, string="本期实收(元)", tracking=True)
    rental_period_no = fields.Integer(default=0, string="期数")
    period_date_from = fields.Date(string="开始日期", default=lambda self: fields.Datetime.today(), tracking=True)

    period_date_to = fields.Date(string="结束日期", default=lambda self: self._get_default_date_end(), tracking=True)
    date_payment = fields.Date(string="支付日期", tracking=True)
    description = fields.Char(string="描述")
    active = fields.Boolean(default=True)

    @api.depends("rental_amount")
    def _get_default_rental_receivable(self):
        for record in self:
            if not record.rental_receivable:
                record.rental_receivable = record.rental_amount

    @api.depends("period_date_from")
    def _get_default_date_end(self):
        for record in self:
            if not record.period_date_to:
                record.period_date_to = estate_lease_contract._get_current_e(record.period_date_from)
                return record.period_date_to

    @api.model
    def write(self, vals):
        _logger.info(f"vals={vals}")
        res = super().write(vals)
        return res

    @api.model
    def create(self, vals_list):
        _logger.info(f"vals_list={vals_list}")
        res = super().create(vals_list)

        return res
