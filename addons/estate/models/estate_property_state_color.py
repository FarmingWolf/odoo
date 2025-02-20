# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EstatePropertyStateColor(models.Model):

    _name = "estate.property.state.color"
    _description = "资产状态颜色设置"

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    state = fields.Selection(
        string='资产状态',
        selection=[('repairing', '整备中'), ('new', '待租中'), ('offer_received', '洽谈中'), ('offer_accepted', '接受报价'),
                   ('sold', '已租'), ('canceled', '已取消'), ('out_dated', '租约已到期')],
        required=True,
    )
    color = fields.Integer(string='Color', required=True)

    def init_state_color(self):
        """自动为当前用户创建所有state的配置记录（如果尚未存在）"""
        states = dict(self._fields['state'].selection)
        for state in states:
            if not self.search([('company_id', '=', self.env.user.company_id.id), ('state', '=', state)]):
                self.create({
                    'company_id': self.env.user.company_id.id,
                    'state': state,
                    'color': 0,  # 默认颜色
                })

        if ('click_from_menu_state_color' in self.env.context) and \
                (self.env.context.get('click_from_menu_state_color') is True):
            action = {
                "name": "租控图颜色设置",
                "type": "ir.actions.act_window",
                "view_mode": "kanban",
                "res_model": "estate.property.state.color",
                "views": [(self.env.ref('estate.view_estate_property_state_color_kanban').id, 'kanban')],
                "context": {
                },
                "domain": [('company_id', 'in', self.env.user.company_ids.ids)],
            }
            return action
