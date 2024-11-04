# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.relativedelta import relativedelta
from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class EstateLeaseContractHeatFeeSetting(models.Model):

    _name = "estate.lease.contract.heat.fee.setting"
    _description = "资产租赁合同取暖费通知单设置"
    _order = "heat_fee_period_e DESC"

    name = fields.Char(string="供暖缴费通知单设置", default="采暖费")

    def _compute_heat_fee_period_s(self):
        if fields.Date.context_today(self).month <= 6:
            tgt_date_s = fields.Date.context_today(self).replace(month=11, day=15) + relativedelta(years=-1)
        else:
            tgt_date_s = fields.Date.context_today(self).replace(month=11, day=15)
        return tgt_date_s

    def _compute_heat_fee_period_e(self):
        if fields.Date.context_today(self).month <= 6:
            tgt_date_e = fields.Date.context_today(self).replace(month=3, day=15)
        else:
            tgt_date_e = fields.Date.context_today(self).replace(month=3, day=15) + relativedelta(years=1)
        return tgt_date_e

    heat_fee_period_s = fields.Date('费用期间开始日', default=_compute_heat_fee_period_s, required=True)
    heat_fee_period_e = fields.Date('费用期间结束日', default=_compute_heat_fee_period_e, required=True)
    heat_fee_price = fields.Float('取暖费单价（元/㎡）', required=True, default=48)
    contact_department = fields.Char(string='落款部门', required=True, default="物业部")

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    def _check_duplicated(self, in_date_s=None, in_date_e=None, self_id=None):

        domain = [('company_id', '=', self.env.user.company_id.id)]
        if self_id:
            domain.append(('id', 'not in', self_id))

        rcds = self.env["estate.lease.contract.heat.fee.setting"].search(domain)

        duplicated_rcds = []
        for rcd in rcds:
            if rcd.heat_fee_period_s <= in_date_s <= rcd.heat_fee_period_e or \
                    rcd.heat_fee_period_s <= in_date_e <= rcd.heat_fee_period_e:
                duplicated_rcds.append({rcd.heat_fee_period_s.strftime('%Y-%m-%d'),
                                        rcd.heat_fee_period_e.strftime('%Y-%m-%d')})

        if duplicated_rcds:
            raise UserError(f"费用期间重复：{duplicated_rcds}，请修改费用期间！")

    @api.model
    def create(self, vals):

        self._check_duplicated(in_date_s=datetime.strptime(vals['heat_fee_period_s'], '%Y-%m-%d').date(),
                               in_date_e=datetime.strptime(vals['heat_fee_period_e'], '%Y-%m-%d').date())

        return super().create(vals)

    @api.model
    def write(self, vals):
        if "heat_fee_period_s" in vals:
            self._check_duplicated(in_date_s=datetime.strptime(vals['heat_fee_period_s'], '%Y-%m-%d').date(),
                                   self_id=self._ids)

        if "heat_fee_period_e" in vals:
            self._check_duplicated(in_date_e=datetime.strptime(vals['heat_fee_period_e'], '%Y-%m-%d').date(),
                                   self_id=self._ids)

        return super().write(vals)
