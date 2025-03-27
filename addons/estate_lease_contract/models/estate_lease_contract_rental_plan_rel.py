# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class EstateLeaseContractRentalPlanRel(models.Model):
    _name = 'estate.lease.contract.rental.plan.rel'
    _description = "合同-资产-租金方案关系表"
    _order = "id"

    sequence = fields.Integer("排序", default=1)

    contract_id = fields.Many2one('estate.lease.contract', string='合同', required=True, ondelete='cascade')
    property_id = fields.Many2one('estate.property', string='资产', required=True)
    rental_plan_id = fields.Many2one('estate.lease.contract.rental.plan', string='租金方案')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    # 合同中的资产租赁信息——合同资产历史信息，主要是不在租金方案中、也不应随着资产master数据变化而变化的合同历史信息↓↓↓按需增补
    contract_renter_id = fields.Many2one('res.partner', string='承租人', related="contract_id.renter_id")
    contract_property_name = fields.Char('资产名称', translate=True)
    contract_property_state = fields.Selection(string='资产状态',
                                               selection=[('repairing', '整备中'), ('new', '待租中'),
                                                          ('offer_received', '洽谈中'), ('offer_accepted', '接受报价'),
                                                          ('sold', '已租'), ('canceled', '已取消'),
                                                          ('out_dated', '租约已到期')],
                                               )
    contract_property_rent_price = fields.Float(related="rental_plan_id.rent_price", string="租金单价（元/天/㎡）")
    contract_property_including_management_fee = fields.Boolean(related="rental_plan_id.including_management_fee",
                                                                string="含物业费")
    contract_property_building_area = fields.Float(default=0.0, string="建筑面积(㎡)")  # 可能拆铺合铺
    contract_property_area = fields.Float(default=0.0, string="面积(㎡)")
    contract_rent_amount_monthly = fields.Float(string="月租金(元)", default=0)
    contract_rent_amount_year = fields.Float(string="年租金(元)", default=0)
    contract_rent_payment_method = fields.Char(string="付款方式")
    contract_deposit_months = fields.Float(string="押金月数", default=0)
    contract_deposit_amount = fields.Float(string="押金(元)", default=0)
    deposit_receivable = fields.Float(string="押金应收(元)", default=lambda self: self.contract_deposit_amount)
    contract_deposit_amount_received = fields.Float(string="押金实收(元)", default=0, compute="_calc_deposit_received")
    contract_deposit_amount_arrears = fields.Float(string="押金欠缴(元)",
                                                   default=lambda self: (self.deposit_receivable -
                                                                         self.contract_deposit_amount_received),
                                                   compute="_calc_deposit_received")
    contract_property_deposit_ids = fields.One2many(comodel_name="estate.lease.contract.property.deposit",
                                                    inverse_name="contract_rental_plan_rel_id", string="押金收缴明细")

    contract_property_fee_water_ids = fields.One2many(comodel_name="estate.lease.contract.property.fee.water",
                                                      inverse_name="contract_rental_plan_rel_id", string="水费明细")
    contract_property_fee_electricity_ids = fields.One2many(
        comodel_name="estate.lease.contract.property.fee.electricity",
        inverse_name="contract_rental_plan_rel_id", string="电费明细")
    contract_property_fee_electricity_maintenance_ids = fields.One2many(
        comodel_name="estate.lease.contract.property.fee.electricity.maintenance",
        inverse_name="contract_rental_plan_rel_id", string="电力维护费明细")
    contract_property_fee_maintenance_ids = fields.One2many(
        comodel_name="estate.lease.contract.property.fee.maintenance",
        inverse_name="contract_rental_plan_rel_id", string="物业费明细")
    fee_maintenance_err_msg = fields.Text("物业费错误信息", readonly=True, compute="_compute_fee_maintenance_err_msg")

    contract_property_tax_ids = fields.One2many(comodel_name="estate.lease.contract.property.tax",
                                                inverse_name="contract_rental_plan_rel_id", string="房产税收缴明细")
    contract_property_tax_amount = fields.Float(string="房产税(元)", default=0)
    property_tax_receivable = fields.Float(string="房产税应收(元)", default=lambda self: self.contract_property_tax_amount)
    property_tax_amount_received = fields.Float(string="房产税实收(元)", default=0,
                                                compute="_calc_property_tax_received")
    property_tax_amount_arrears = fields.Float(string="房产税欠缴(元)",
                                               default=lambda self: (self.property_tax_receivable -
                                                                     self.property_tax_amount_received),
                                               compute="_calc_property_tax_received")

    _sql_constraints = [
        ('contract_property_rental_plan_unique', 'unique(contract_id, property_id)',
         "同一合同内，同一资产，不能有不同的租金方案"),
    ]

    def _compute_fee_maintenance_err_msg(self):
        for record in self:
            record.fee_maintenance_err_msg = None
            record.contract_id._bind_manage_fee_detail_fee_maintenance()
            # if record.fee_maintenance_err_msg:
            #     raise UserError(record.fee_maintenance_err_msg)

    @api.depends("contract_property_deposit_ids")
    def _calc_deposit_received(self):
        for record in self:
            received = 0
            for deposit_rcd in record.contract_property_deposit_ids:
                received += deposit_rcd.deposit_received
            record.contract_deposit_amount_received = received
            record.contract_deposit_amount_arrears = record.deposit_receivable - received

    @api.onchange("contract_property_deposit_ids")
    def _onchange_deposit_received(self):
        received = 0
        for deposit_rcd in self.contract_property_deposit_ids:
            received += deposit_rcd.deposit_received
        self.contract_deposit_amount_received = received
        self.contract_deposit_amount_arrears = self.deposit_receivable - received

    def action_confirm_deposit_received(self):
        for record in self:
            # 防止空点
            if abs(record.deposit_receivable - record.contract_deposit_amount_received) < 0.01:
                continue

            received_bef = record.contract_deposit_amount_received
            received_aft = record.deposit_receivable

            record.contract_deposit_amount_received = received_aft
            # 增加相应的分次收缴明细
            deposit_detail = [{
                "contract_rental_plan_rel_id": record.id,
                "deposit_received": received_aft - received_bef,
            }]
            self.env["estate.lease.contract.property.deposit"].create(deposit_detail)

    @api.depends("contract_property_tax_ids")
    def _calc_property_tax_received(self):
        for record in self:
            received = 0
            for property_tax_rcd in record.contract_property_tax_ids:
                received += property_tax_rcd.tax_received
            record.property_tax_amount_received = received
            record.property_tax_amount_arrears = record.property_tax_receivable - received

    @api.onchange("contract_property_tax_ids")
    def _onchange_property_tax_received(self):
        received = 0
        for property_tax_rcd in self.contract_property_tax_ids:
            received += property_tax_rcd.tax_received
        self.property_tax_amount_received = received
        self.property_tax_amount_arrears = self.property_tax_receivable - received

    def action_confirm_property_tax_received(self):
        for record in self:
            # 防止空点
            if abs(record.property_tax_receivable - record.property_tax_amount_received) < 0.01:
                continue

            received_bef = record.property_tax_amount_received
            received_aft = record.property_tax_receivable

            record.property_tax_amount_received = received_aft
            # 增加相应的分次收缴明细
            property_tax_detail = [{
                "contract_rental_plan_rel_id": record.id,
                "tax_received": received_aft - received_bef,
            }]
            self.env["estate.lease.contract.property.tax"].create(property_tax_detail)

    def _check_date_overlap(self, check_tgt_nm):
        """检查日期范围是否有重叠
            不允许部分重叠而允许完全重叠的日期可以理解为多次缴纳
        """
        lines = []
        for record in self:
            if check_tgt_nm == "水费":
                lines = record.contract_property_fee_water_ids
            if check_tgt_nm == "电费":
                lines = record.contract_property_fee_electricity_ids
            if check_tgt_nm == "电力维护费":
                lines = record.contract_property_fee_electricity_maintenance_ids
            if check_tgt_nm == "物业费":
                lines = record.contract_property_fee_maintenance_ids

            i = 0
            for line in lines:
                # 物业费实缴明细的期间特殊处理，由于物业费实收明细可以在两个页面编辑创建数据，
                # 如果是在物业费明细页面创建的数据，页面并无期间设置，理论上开始日终了日不应该出现问题，
                # 如果是在租赁标的页面创建的实收数据，原则上应该在租赁标的页面修改（那里有错误信息提示），如果在这里强行校验，
                # 会出现一旦修改了物业费计费周期的情况，页面被校验卡住无法修改也无法删除
                if check_tgt_nm == "物业费":
                    break

                ii = 0
                for comp_tgt in lines:
                    if i != ii:

                        if comp_tgt.period_d_start < line.period_d_start <= comp_tgt.period_d_end:
                            raise ValidationError(f"{check_tgt_nm}期间的开始日设置错误：开始日期[{line.period_d_start}]介于"
                                                  f"[{comp_tgt.period_d_start}]~[{comp_tgt.period_d_end}]")

                        if comp_tgt.period_d_start <= line.period_d_end < comp_tgt.period_d_end:
                            raise ValidationError(f"{check_tgt_nm}期间的结束日设置错误：结束日期[{line.period_d_end}]介于"
                                                  f"[{comp_tgt.period_d_start}]~[{comp_tgt.period_d_end}]")

                    ii += 1

                i += 1

    @api.model
    def create(self, vals):
        record = super().create(vals)
        check_tgt = ['水费', '电费', '电力维护费', '物业费']
        for tgt in check_tgt:
            record._check_date_overlap(tgt)

        return record

    @api.model
    def write(self, vals):

        res = super().write(vals)
        check_tgt = ['水费', '电费', '电力维护费', '物业费']
        for tgt in check_tgt:
            self._check_date_overlap(tgt)

        return res
