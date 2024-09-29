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


class EstateLeaseContractPropertyIniState(models.Model):
    _name = "estate.lease.contract.property.ini.state"
    _description = "资产租赁合同资产初始状态"
    _order = "contract_id, property_id"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    contract_id = fields.Many2one('estate.lease.contract', string="合同", ondelete="cascade", readonly=True, store=True,
                                  default=lambda self: self._get_context_contract_id(),
                                  compute="_compute_contract_id")
    property_id = fields.Many2one('estate.property', string="租赁标的", ondelete="cascade", readonly=True, store=True,
                                  default=lambda self: self._get_context_property_id(),
                                  compute="_compute_property_id")

    def _get_context_contract_id(self):
        if "CONTRACT_ID" in self.env.context:
            self.contract_id = self.env.context["CONTRACT_ID"]
            return self.env.context["CONTRACT_ID"]

    def _get_context_property_id(self):
        if "PROPERTY_ID" in self.env.context:
            self.property_id = self.env.context["PROPERTY_ID"]
            return self.env.context["PROPERTY_ID"]

    def _compute_contract_id(self):
        for record in self:
            if "CONTRACT_ID" in self.env.context:
                record.contract_id = self.env.context["CONTRACT_ID"]
            else:
                record.contract_id = record.contract_id

    def _compute_property_id(self):
        for record in self:
            if "PROPERTY_ID" in self.env.context:
                record.property_id = self.env.context["PROPERTY_ID"]
            else:
                record.property_id = record.property_id

    def _get_property_options(self):
        rcd = self.env['estate.lease.contract.property.ini.state'].search([('contract_id', '=', self.contract_id.id)])
        options = {(r.property_id.id, r.property_id.name) for r in rcd}
        return options

    property_id_sel = fields.Selection(string="资产", selection=_get_property_options, store=False)

    image_1920 = fields.Image(string="初始状态图", max_width=1920, max_height=1920)

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    active = fields.Boolean(string="有效", default=True)

    @api.model
    def default_get(self, in_fields):
        res = super().default_get(in_fields)
        if 'contract_id' in in_fields and self._context.get('CONTRACT_ID'):
            res.update({
                'contract_id': self._context.get('CONTRACT_ID')
            })
        if 'property_id' in in_fields and self._context.get('PROPERTY_ID'):
            _logger.info(f"self._context.get-PROPERTY_ID={self._context.get('PROPERTY_ID')}")
            res.update({
                'property_id': self._context.get('PROPERTY_ID')
            })
        return res

    @api.model
    def write(self, vals):
        res = super().write(vals)

        # tgt_ids = []
        # records = self.env['estate.lease.contract.property.ini.state'].browse(self.ids)
        # for record in records:
        #     if (not record.property_id) or (not record.image_1920):
        #         record.unlink()
        #     else:
        #         tgt_ids.append(record.id)
        #
        # for record in self:
        #     if record.id not in tgt_ids:
        #         record.unlink()

        return res
