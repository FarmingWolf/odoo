# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OperationContractEventSettleAccountGroup(models.Model):
    _name = "operation.contract.event.settle.account.group"
    _description = "以活动/合同作为结算组"
    _order = "id DESC"

    name = fields.Char(string="结算组名", compute="_compute_name_display")
    event_id = fields.Many2one('event.event', string='活动', ondelete='restrict',
                               domain=[('stage_id.sequence', '>=', 50), ('stage_id.sequence', '<=', 90)],
                               compute="_compute_event_id", readonly=False, store=True)
    operation_contract_id = fields.Many2one('operation.contract.contract', string='合同', ondelete='restrict',
                                            domain=[('stage_id.sequence', '>=', 100), ('stage_id.sequence', '<=', 200)],
                                            compute="_compute_operation_contract_id", readonly=False, store=True)
    operation_contract_event_settle_account_ids = fields.One2many('operation.contract.event.settle.account', 'group_id',
                                                                  string="事项清单")
    op_date_time = fields.Date('结算日期', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends('operation_contract_id')
    def _compute_event_id(self):
        for record in self:
            if record.operation_contract_id:
                record.event_id = self.env['event.event'].search(
                    [('reference_contract_id', '=', record.operation_contract_id.id)], limit=1)

    @api.depends('event_id')
    def _compute_operation_contract_id(self):
        for record in self:
            if record.event_id:
                record.operation_contract_id = record.event_id.reference_contract_id
            else:
                record.operation_contract_id = False

    @api.depends('event_id', 'operation_contract_id')
    def _compute_name_display(self):
        for record in self:
            if record.event_id:
                record.name = record.event_id.name
            elif record.operation_contract_id:
                record.name = record.operation_contract_id.name
            else:
                _logger.info(f"record.name被设置为空")
                record.name = False  # 原则上这分支不应该存在

    _sql_constraints = [("event_or_operation_contract_required",
                         "CHECK(event_id IS NOT NULL OR operation_contract_id IS NOT NULL)", "活动/合同，至少选一项！"), ]

    # @api.constrains('event_id', 'operation_contract_id')
    # def _check_description(self):
    #     for record in self:
    #         _logger.info(f"record.event_id={record.event_id.id}")
    #         _logger.info(f"record.operation_contract_id={record.operation_contract_id.id}")
    #         if not record.event_id and not record.operation_contract_id:
    #             raise ValidationError("活动/合同，至少选一项吧？")
    #
    #         if record.event_id:
    #             self._compute_event_id()
    #
    #         if record.operation_contract_id:
    #             self._compute_operation_contract_id()

    def _check_event_contract_consistency(self, event_id, contract_id):
        if not event_id and not contract_id:
            raise ValidationError("活动/合同，至少选一项吧？")

        _logger.info(f"_check_event_contract_consistency event_id={event_id};contract_id={contract_id}")
        er_str = "活动/合同不一致，建议：通过选择活动确定合同，或者选择合同确定活动后，请不要删除自动匹配出的数据！"
        if event_id:
            events = self.env['event.event'].search([('id', '=', event_id)], limit=1).mapped('reference_contract_id')
            for contract in events:
                if contract_id:
                    if contract[0]:
                        _logger.info(
                            f"if contract_id != contract[0]: contract_id={contract_id};contract[0]={contract[0]}")
                        if contract_id != contract[0].id:
                            raise ValidationError(er_str)
                    else:
                        raise ValidationError(er_str)
                else:
                    if contract[0]:
                        raise ValidationError(er_str)

        if contract_id:
            events = self.env['event.event'].search(
                [('reference_contract_id', '=', contract_id)], limit=1).mapped('id')  # event表里的id不可能空,且这里居然是int
            for contract in events:
                if event_id:
                    if event_id != contract:
                        raise ValidationError(er_str)
                else:
                    raise ValidationError(er_str)

    @api.model
    def create(self, vals_list):

        if not vals_list['event_id'] and not vals_list['operation_contract_id']:
            raise ValidationError("活动/合同，至少选一项吧？")

        _logger.info(f"vals_list['event_id']={vals_list['event_id']}")
        _logger.info(f"vals_list['operation_contract_id']={vals_list['operation_contract_id']}")
        self._check_event_contract_consistency(vals_list['event_id'], vals_list['operation_contract_id'])

        return super().create(vals_list)

    def write(self, values):
        # self._check_description()
        for record in self:
            if 'event_id' in values:
                event_id = values['event_id']
                _logger.info(f"write values['event_id']={event_id}")
            else:
                event_id = record.event_id.id
                _logger.info(f"write record.event_id.id={event_id}")

            if 'operation_contract_id' in values:
                operation_contract_id = values['operation_contract_id']
                _logger.info(f"write values['operation_contract_id']={operation_contract_id}")
            else:
                operation_contract_id = record.operation_contract_id.id
                _logger.info(f"write record.operation_contract_id.id={operation_contract_id}")

            self._check_event_contract_consistency(event_id, operation_contract_id)

        return super().write(values)


class OperationContractEventSettleAccount(models.Model):
    _name = 'operation.contract.event.settle.account'
    _description = '依据活动具体情况进行合同结算'
    _order = 'group_id DESC, sequence ASC'

    # 结算组是个逻辑概念，实际业务中以活动/合同为分组
    group_id = fields.Many2one("operation.contract.event.settle.account.group", string="结算组", required=True,
                               ondelete='cascade')
    business_items_id = fields.Many2one('business.items', string='结算事项', required=True)
    accounting_subject_id = fields.Many2one('accounting.subject.subject', string="会计科目", required=True)
    settle_amount = fields.Float(string="金额（元）", required=True, digits=(12, 2))
    description = fields.Text(string='备注', translate=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    sequence = fields.Integer(string='序号', default=_default_sequence)
