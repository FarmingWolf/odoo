# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class ContractExpenseCategory(models.Model):

    _name = "contract.expense.category"
    _description = "支付类合同流程类别（一般情况下，影响因素有合同金额等字段）"
    _order = "sequence, name, amount_min ASC"

    name = fields.Char(string='合同流程类别', required=True)
    amount_min = fields.Float(string="最小金额(From)", required=True, default=0.0, copy=False,
                              help="含最小金额，不含最大金额，如： 0 ≤ X<50000 最大金额为0时，代表无最大金额限制。")
    amount_max = fields.Float(string="最大金额(To)", default=None, copy=False)

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    active = fields.Boolean(default=True)

    approval_stages = fields.One2many(comodel_name='contract.expense.approval.stage', inverse_name='category_id',
                                      string="审批节点")
    meeting_minute_types = fields.Many2many(comodel_name="meeting.minutes.type",
                                            relation="cec_meeting_minutes_type_relation",
                                            column1="category_id", column2="meeting_minutes_type_id",
                                            string="附件类型")
    overdue_reminder_hours = fields.Float(string="超期小时数", default=72, copy=True)
    sequence = fields.Integer(string="序号", default=0)
    editable = fields.Boolean(default=lambda self: self._compute_editable(), compute='_compute_editable')
    contract_expense_ids = fields.One2many("contract.expense", 'category_id', string="合同")

    def _compute_editable(self):
        ret_editable = self.env.user.has_group('contract_expense.group_contract_expense_manager')
        self.editable = ret_editable
        return ret_editable

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

    def action_contract_expense_approval_setting(self):

        action = {
            "name": f"设置审批流:【{self.name}】【{self.amount_min}至{self.amount_max if self.amount_max else '无限大'}】",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "contract.expense.approval.stage",
            "context": {"default_category": self.id},
            "views": [
                (self.env.ref('contract_expense.contract_expense_approval_stage_view_tree').id, 'tree'),
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

    def _check_application_exists(self):
        # todo 应考虑
        #  1、属于该分类的审批流已经存在的情况下是否还允许修改流程分类，允许修改哪些字段？
        #  2、流程作废应如何应对；
        pass
