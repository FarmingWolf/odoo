# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstateLeaseContractApprovalSwitch(models.Model):

    _name = "estate.lease.contract.approval.switch"
    _description = "资产租赁合同审批流启用开关"

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    approval_switch = fields.Boolean(string="启用租赁合同审批流", default=False)

    def init_approval_switch(self):
        if not self.search([('company_id', '=', self.env.user.company_id.id)]):
            self.create({
                'company_id': self.env.user.company_id.id,
                'approval_switch': False,  # 默认不启用
            })

        if ('click_from_menu_approval_switch' in self.env.context) and \
                (self.env.context.get('click_from_menu_approval_switch') is True):

            approval_switch_rcd = self.search([('company_id', '=', self.env.user.company_id.id)], limit=1)

            action = {
                "name": "设置租赁合同审批流",
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "estate.lease.contract.approval.switch",
                "views": [(self.env.ref('estate_lease_contract.estate_lease_contract_approval_switch_form').id,
                           'form')],
                "context": {
                },
                "res_id": approval_switch_rcd[0].id,
                "domain": [('company_id', 'in', self.env.user.company_ids.ids)],
            }
            return action

    def action_open_approval_state_set(self):
        action = {
            "name": "设置租赁合同审批流",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "estate.lease.contract.approval.stage",
            "views": [
                (self.env.ref('estate_lease_contract.estate_lease_contract_approval_stage_view_tree').id, 'tree'),
                (False, 'form')],
            "domain": [('company_id', 'in', self.env.user.company_ids.ids)],
        }
        return action
