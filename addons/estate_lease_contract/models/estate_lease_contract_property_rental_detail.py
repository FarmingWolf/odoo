# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from typing import Dict, List

from odoo import fields, models, api


class EstateLeaseContractPropertyRentalDetail(models.Model):

    _name = "estate.lease.contract.property.rental.detail"
    _description = "资产租赁合同租金明细"
    _order = "id"

    contract_id = fields.Many2one('estate.lease.contract', string="合同")
    property_id = fields.Many2one('estate.property', string="租赁标的")
    rental_amount = fields.Float(default=0.0, string="本期租金(元)")
    rental_amount_zh = fields.Char(string="本期租金(元)大写")
    rental_receivable = fields.Float(default=0.0, string="本期应收(元)", compute="_get_default_rental_receivable")
    rental_received = fields.Float(default=0.0, string="本期实收(元)")
    rental_period_no = fields.Integer(default=0, string="期数")
    period_date_from = fields.Date(string="开始日期")
    period_date_to = fields.Date(string="结束日期")
    date_payment = fields.Date(string="支付日期")
    description = fields.Char(string="描述")

    @api.depends("rental_amount")
    def _get_default_rental_receivable(self):
        for record in self:
            record.rental_receivable = record.rental_amount
