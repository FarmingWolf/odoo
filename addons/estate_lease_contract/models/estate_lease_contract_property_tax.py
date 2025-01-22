# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from math import ceil, floor
from typing import Dict, List

from odoo.exceptions import UserError
from odoo.tools import start_of, end_of
from . import estate_lease_contract
from odoo import fields, models, api
from ...utils.models.utils import Utils

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyTax(models.Model):
    _name = "estate.lease.contract.property.tax"
    _description = "Property Tax"
    _order = "date_received"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    contract_rental_plan_rel_id = fields.Many2one(comodel_name='estate.lease.contract.rental.plan.rel',
                                                  string='合同-资产关系表ID', required=True, ondelete="cascade")
    tax_receivable_this = fields.Float(default=0.0, string="本次应收(元)", compute="_compute_received",
                                       store=True, compute_sudo=True)
    tax_received = fields.Float(default=0.0, string="本次实收(元)", tracking=True)

    date_received = fields.Date(string="实收日期", default=lambda self: fields.Date.context_today(self), tracking=True)
    tax_received_sum = fields.Float(default=0.0, string="累计实收(元)", readonly=True, compute="_compute_received",
                                    store=True, compute_sudo=True)
    tax_arrears = fields.Float(string="欠缴金额", readonly=True, store=True, compute="_compute_received",
                               compute_sudo=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True,
                                 ondelete="cascade")

    # 以下字段要在页面显示
    property_id = fields.Many2one('estate.property', related="contract_rental_plan_rel_id.property_id", string="资产",
                                  ondelete="cascade")
    contract_id = fields.Many2one('estate.lease.contract', related="contract_rental_plan_rel_id.contract_id",
                                  string="合同", ondelete="cascade")
    contract_state = fields.Selection(related="contract_id.state", string="合同状态")
    party_a_unit_id = fields.Many2one("estate.lease.contract.party.a.unit", related="contract_id.party_a_unit_id",
                                      ondelete="set null")
    party_a_unit_invisible = fields.Boolean(string="甲方显示与否", related="contract_id.party_a_unit_invisible")
    date_start = fields.Date(string="合同开始日期", related="contract_id.date_start")
    date_rent_start = fields.Date(string="计租开始日期", related="contract_id.date_rent_start")
    date_rent_end = fields.Date(string="计租结束日期", related="contract_id.date_rent_end")
    renter_id = fields.Many2one('res.partner', string="承租人", related='contract_id.renter_id', store=True,
                                ondelete="set null")
    contract_amount = fields.Float(string="合同总额（元）", related='contract_id.contract_amount')
    tax_receivable = fields.Float(string="房产税应收（元）", related='contract_rental_plan_rel_id.property_tax_receivable')

    @api.depends("tax_received", "date_received")
    def _compute_received(self):
        for record in self:
            domain = [('contract_rental_plan_rel_id', '=', record.contract_rental_plan_rel_id.id)]
            rcds = self.env["estate.lease.contract.property.tax"].search(domain)
            received_sum = 0.0

            for rcd in rcds:
                received_sum += rcd.tax_received
                if rcd.tax_received_sum != received_sum:
                    rcd.tax_received_sum = received_sum

                if record.contract_rental_plan_rel_id.property_tax_receivable:
                    tax_arrears = record.contract_rental_plan_rel_id.property_tax_receivable - rcd.tax_received_sum
                    if rcd.tax_arrears != tax_arrears:
                        rcd.tax_arrears = tax_arrears

                    # 根据本次实收和本次欠缴反算本次应收（不同于总应收）
                    if rcd.tax_receivable_this != rcd.tax_received + rcd.tax_arrears:
                        rcd.tax_receivable_this = rcd.tax_received + rcd.tax_arrears

            tax_arrears = record.contract_rental_plan_rel_id.property_tax_receivable - record.tax_received_sum
            if record.tax_arrears != tax_arrears:
                record.tax_arrears = tax_arrears
            # 根据本次实收和本次欠缴反算本次应收（不同于总应收）
            if record.tax_receivable_this != record.tax_received + record.tax_arrears:
                record.tax_receivable_this = record.tax_received + record.tax_arrears

            # 更新回到父级记录
            record.contract_rental_plan_rel_id.property_tax_amount_received = received_sum
            record.contract_rental_plan_rel_id.property_tax_amount_arrears = \
                record.contract_rental_plan_rel_id.property_tax_receivable - received_sum
