# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta, datetime
from math import ceil, floor
from typing import Dict, List

from odoo.exceptions import UserError
from odoo.tools import start_of, end_of
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyFeeMaintenance(models.Model):
    _name = "estate.lease.contract.property.fee.maintenance"
    _description = "资产租赁合同物业费"
    _order = "date_received"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    contract_rental_plan_rel_id = fields.Many2one(comodel_name='estate.lease.contract.rental.plan.rel',
                                                  string='合同-资产关系表ID', required=True, ondelete="cascade")
    period_d_start = fields.Date(string="本期开始日", default=lambda self: self._cal_period_d_start(), tracking=True)
    period_d_end = fields.Date(string="本期结束日", default=lambda self: self._cal_period_d_end(), tracking=True)
    maintenance_receivable = fields.Float(default=0.0, string="本期应收(元)", tracking=True, help="账单金额")
    maintenance_received = fields.Float(default=0.0, string="本期实收(元)", tracking=True)

    date_received = fields.Date(string="实收日期", default=lambda self: fields.Date.context_today(self), tracking=True)
    maintenance_received_sum = fields.Float(default=0.0, string="累计实收(元)", readonly=True, compute="_compute_received",
                                            store=True, compute_sudo=True, help="合同保存后，系统自动计算累计值")
    maintenance_arrears = fields.Float(string="本期欠缴(元)", readonly=True, store=True, compute="_compute_received",
                                       compute_sudo=True)
    maintenance_arrears_sum = fields.Float(string="累计欠缴(元)", readonly=True, store=True, compute="_compute_received",
                                           compute_sudo=True, help="合同保存后，系统自动计算累计值")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True,
                                 ondelete="cascade")

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
    maintenance_receipt = fields.Boolean(string="发票")
    maintenance_receipt_evidence = fields.Html(string="发票信息")

    @api.onchange("maintenance_receivable", "maintenance_received")
    def _onchange_maintenance_receivable(self):
        self.maintenance_arrears = self.maintenance_receivable - self.maintenance_received

    @api.onchange("period_d_start", "period_d_end")
    def _onchange_period_d_start(self):
        if self.period_d_start > self.period_d_end:
            self.period_d_end = end_of(self.period_d_start, 'month')

    def _cal_period_d_start(self):
        context_d = fields.Date.context_today(self)
        start_d = start_of(context_d, 'month')
        return start_d

    def _cal_period_d_end(self):
        context_d = fields.Date.context_today(self)
        end_d = end_of(context_d, 'month')
        return end_d

    # @api.model_create_multi
    # def create(self, vals_list):
    #
    #     # create时，还没有self
    #     # _logger.info(f"create contract_id={self.contract_rental_plan_rel_id.contract_id.id};"
    #     #              f"property_id={self.contract_rental_plan_rel_id.property_id.id}")
    #     # _logger.info(f"vals_list={vals_list}")
    #     self._check_multi_date_duplicate(vals_list)
    #
    #     return super().create(vals_list)
    #
    # @api.model
    # def write(self, values):
    #     _logger.info(f"update contract_id={self.contract_rental_plan_rel_id.contract_id.id};"
    #                  f"property_id={self.contract_rental_plan_rel_id.property_id.id}")
    #     _logger.info(f"values={values}")
    #
    #     self._check_update_date_duplicate(values)
    #     return super().write(values)

    @api.depends("maintenance_received", "maintenance_receivable", "date_received")
    def _compute_received(self):
        for record in self:
            domain = [('contract_rental_plan_rel_id', '=', record.contract_rental_plan_rel_id.id)]
            rcds = self.env["estate.lease.contract.property.fee.maintenance"].search(domain)
            received_sum = 0.0
            arrears_sum = 0.0

            for rcd in rcds:
                received_sum += rcd.maintenance_received
                if rcd.maintenance_received_sum != received_sum:
                    rcd.maintenance_received_sum = received_sum

                arrears = rcd.maintenance_receivable - rcd.maintenance_received
                arrears_sum += arrears
                if rcd.maintenance_arrears != arrears:
                    rcd.maintenance_arrears = arrears

                if rcd.maintenance_arrears_sum != arrears_sum:
                    rcd.maintenance_arrears_sum = arrears_sum

    # def _check_multi_date_duplicate(self, vals_list):
    #     i = 0
    #     for new_vals in vals_list:
    #         # 先查本行
    #         if 'period_d_start' in new_vals and 'period_d_end' in new_vals and \
    #                 new_vals['period_d_start'] > new_vals['period_d_end']:
    #             raise UserError(f"物业费期间的开始结束日期设置错误："
    #                             f"[{new_vals['period_d_start']}]~[{new_vals['period_d_end']}]")
    #
    #         # 再自查页面数据自身是否有期间交叉
    #         ii = 0
    #         for comp_tgt in vals_list:
    #             if i != ii:
    #                 if ('period_d_start' in new_vals and 'period_d_start' in comp_tgt and 'period_d_end' in comp_tgt
    #                         and comp_tgt['period_d_start'] < new_vals['period_d_start'] <= comp_tgt['period_d_end']):
    #                     raise UserError(f"物业费期间的期间设置重叠错误：开始日期[{new_vals['period_d_start']}]介于"
    #                                     f"[{comp_tgt['period_d_start']}]~[{comp_tgt['period_d_end']}]")
    #
    #                 if ('period_d_end' in new_vals and 'period_d_start' in comp_tgt and 'period_d_end' in comp_tgt
    #                         and comp_tgt['period_d_start'] <= new_vals['period_d_end'] < comp_tgt['period_d_end']):
    #                     raise UserError(f"物业费期间的期间设置重叠错误：结束日期[{new_vals['period_d_end']}]介于"
    #                                     f"[{comp_tgt['period_d_start']}]~[{comp_tgt['period_d_end']}]")
    #
    #             ii += 1
    #
    #         fees_exist = False
    #         if not fees_exist:
    #             _logger.info(f"self.contract_rental_plan_rel_id.id={self.contract_rental_plan_rel_id.id}")
    #             domain = [('contract_rental_plan_rel_id', '=', self.contract_rental_plan_rel_id.id)]
    #             fees_exist = self.search(domain)
    #             _logger.info(f"fees_exist={fees_exist}")
    #
    #         # 仅做期间的部分重叠交叉校验，而完全的覆盖重叠不算错误
    #         # 比如 20250101-20250131与20250102-20250201算错误
    #         for fee in fees_exist:
    #             if 'period_d_start' in new_vals:
    #                 tgt_date = datetime.strptime(new_vals['period_d_start'], '%Y-%m-%d').date()
    #                 if fee.period_d_start < tgt_date <= fee.period_d_end:
    #                     raise UserError(f"物业费期间的期间重叠了：开始日期[{new_vals['period_d_start']}]介于"
    #                                     f"[{fee.period_d_start}]~[{fee.period_d_end}]")
    #
    #             if 'period_d_end' in new_vals:
    #                 tgt_date = datetime.strptime(new_vals['period_d_end'], '%Y-%m-%d').date()
    #                 if fee.period_d_start <= tgt_date < fee.period_d_end:
    #                     raise UserError(f"物业费期间的期间重叠了：结束日期[{new_vals['period_d_end']}]介于"
    #                                     f"[{fee.period_d_start}]~[{fee.period_d_end}]")
    #
    #         i += 1
    #
    # def _check_update_date_duplicate(self, new_vals):
    #     if not new_vals or len(new_vals) == 0:
    #         return
    #
    #     if 'period_d_start' not in new_vals and 'period_d_end' not in new_vals:
    #         return
    #
    #     tgt_list = [new_vals]
    #     self._check_multi_date_duplicate(tgt_list)
