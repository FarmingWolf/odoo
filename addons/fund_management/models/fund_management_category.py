# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class FundManagementCategory(models.Model):

    _name = "fund.management.category"
    _description = "Fund Management Category"
    _order = "sequence, name, amount_min ASC"

    name = fields.Char(string='Fund Management Category', required=True,
                       help="Please do not include spaces in the category name")
    amount_min = fields.Float(string="Fund range(From)", required=True, default=0.0, copy=False,
                              help="Contains lower limit value, not upper limit value. e.g. 0 ≤ X<50000 \n"
                                   "The upper limit value of 0 represents infinity.")
    amount_max = fields.Float(string="Fund range(To)", default=None, copy=False)
    contract_payment = fields.Boolean(string="Contract Payment", default=True, copy=False)

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    active = fields.Boolean(default=True)

    approval_stages = fields.One2many(comodel_name='fund.management.approval.stage', inverse_name='category_id',
                                      string="Approval Stages")
    meeting_minute_types = fields.Many2many(comodel_name="fund.management.meeting.minutes.type",
                                            relation="category_meeting_minutes_type_rel",
                                            column1="category_id", column2="meeting_minutes_type_id",
                                            string="Meeting Minutes Type")
    sequence = fields.Integer(string="sequence", default=0)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._check_amount_range()
        return record

    def write(self, vals):
        res = super().write(vals)
        self._check_amount_range()
        self._check_application_exists()
        return res

    def copy(self, default=None):

        if default is None:
            default = {}

        default.update({
            'amount_min': self.amount_max,
            'amount_max': self.amount_max + self.amount_min,
        })
        return super().copy(default)

    def action_fund_management_approval_setting(self):

        action = {
            "name": f"设置审批流:【{self.name}】【{self.amount_min}至{self.amount_max if self.amount_max else '无限大'}】",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "fund.management.approval.stage",
            "context": {"default_category": self.id},
            "views": [
                (self.env.ref('fund_management.fund_management_approval_stage_view_tree').id, 'tree'),
                (False, 'form')],
            "domain": [('company_id', 'in', self.env.user.company_ids.ids), ('category_id', '=', self.id)],
        }
        return action

    def _check_amount_range(self):
        for rcd in self:
            if rcd.amount_min >= rcd.amount_max:
                # amount_max = 0 代表无限大
                if rcd.amount_max == 0:
                    pass
                else:
                    raise ValidationError(f"资金范围(至)【{rcd.amount_max}】必须比资金范围(自)【{rcd.amount_min}】大")

            records_exist = self.search([('name', '=', rcd.name)])
            _logger.info(f"records_exist={records_exist}")
            _logger.info(f"rcd.id={rcd.id}")

            for db_rcd in records_exist:
                if rcd.id == db_rcd.id:
                    continue
                _logger.info(f"rcd.amount_min={rcd.amount_min}；"
                             f"db_rcd.amount_min={db_rcd.amount_min}；"
                             f"db_rcd.amount_max={db_rcd.amount_max}")
                if rcd.amount_min >= db_rcd.amount_min:
                    if db_rcd.amount_max:
                        if rcd.amount_min < db_rcd.amount_max:
                            raise ValidationError(f"本条数据的资金范围与{db_rcd.name}："
                                                  f"{db_rcd.amount_min}~{db_rcd.amount_max}重复了。")
                    else:
                        # db_rcd.amount_max 没有值或=0代表无限大
                        raise ValidationError(f"本条数据的资金范围与{db_rcd.name}："
                                              f"[{db_rcd.amount_min}~无限大]重复了。")

    def action_select_category_create_application(self):

        default_category_id = self.env.context.get('default_category_id')
        _logger.info(f"default_category_id={default_category_id}")
        request.session["default_category_id"] = default_category_id

        action = {
            'name': "Create New Fund Management Application",
            'type': 'ir.actions.act_window',
            'res_model': 'fund.management',
            'view_mode': 'form',
            'res_id': False,
            'context': {'default_category_id': default_category_id},
            'target': 'current',
        }
        return action

    def _check_application_exists(self):
        # todo 应考虑
        #  1、属于该分类的审批流已经存在的情况下是否还允许修改流程分类，允许修改哪些字段？
        #  2、流程作废应如何应对；
        pass
