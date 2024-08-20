# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractRentalPlanRel(models.Model):
    _name = 'estate.lease.contract.rental.plan.rel'
    _description = "合同-资产-租金方案关系表"
    _order = "id"

    sequence = fields.Integer("排序", default=1)

    contract_id = fields.Many2one('estate.lease.contract', string='合同', required=True)
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
    contract_property_building_area = fields.Float(default=0.0, string="建筑面积（㎡）")  # 可能拆铺合铺
    contract_property_area = fields.Float(default=0.0, string="面积（㎡）")
    contract_rent_amount_monthly = fields.Float(string="月租金（元）", default=0)
    contract_rent_amount_year = fields.Float(string="年租金(元)", default=0)
    contract_rent_payment_method = fields.Char(string="付款方式")
    contract_deposit_months = fields.Float(string="押金月数", default=0)
    contract_deposit_amount = fields.Float(string="押金金额", default=0)

    _sql_constraints = [
        ('contract_property_rental_plan_unique', 'unique(contract_id, property_id)',
         "同一合同内，同一资产，不能有不同的租金方案"),
    ]
