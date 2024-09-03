# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstateLeaseContractRegistrationAddrRel(models.Model):
    _name = "estate.lease.contract.registration.addr.rel"
    _description = "合同注册地址及关联公司关系表"

    name = fields.Char('注册地址分配', default=lambda self: self._get_name())
    price = fields.Float('分配价格（元）')
    sequence = fields.Integer("排序", default=1)
    contract_id = fields.Many2one(string='合同', comodel_name='estate.lease.contract')
    registration_addr_id = fields.Many2one(string="注册地址", comodel_name="estate.registration.addr")
    party_b_associated_company_id = fields.Many2one(string="分配公司", comodel_name="res.partner")

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.model
    def _get_name(self):
        default_name = self.contract_id.name + self.registration_addr_id.name + self.party_b_associated_company_id.name
        self.name = default_name
        for record in self:
            record.name = record.contract_id.name + record.registration_addr_id.name + \
                          record.party_b_associated_company_id.name
        return default_name


