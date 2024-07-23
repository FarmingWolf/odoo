# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random
from datetime import timedelta, datetime

from odoo.http import request
from odoo.tools.translate import _

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, is_html_empty

_logger = logging.getLogger(__name__)


def _create_approval_detail(self, record, approval_or_reject, is_cancel):

    """ 既然页面已经设置了TZ，那么创建记录时就不应该多此一举，否则页面再选出来时，会多个8小时时差
    timezone = self._context.get('tz') or self.env.user.partner_id.tz or 'Asia/Shanghai'

    _logger.info(f"timezone:{timezone}")
    self_tz = self.with_context(tz=timezone)
    _logger.info(f"self_tz:{self_tz}")
    """

    _logger.info(f"datetime.now()[{datetime.now()}]")
    date_time = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
    _logger.info(f"date:{date_time}")

    approval_by_usr_id = self._get_employee()
    approval_by_usr_nm = self._get_employee_nm()

    if approval_or_reject:
        approval_decision_txt = "同意"
        approval_comment = "同意"
    else:
        approval_decision_txt = "驳回"
        approval_comment = "驳回"

    if record.stage_id.sequence == 0:
        rcd_exists = self.env['operation.contract.approval.detail'].browse(record.approval_detail_ids.ids).exists()

        if rcd_exists:
            approval_comment = "再提交"
        else:
            approval_comment = "新建"

    if is_cancel:
        approval_decision_txt = "取消"
        approval_comment = "取消"

    self.env['operation.contract.approval.detail'].create({
        'contract_id': f"{record.id}",
        'approval_stage': f"{record.stage_id.id}",
        'approval_stage_id': f"{record.stage_id.id}",
        'approval_stage_nm': f"{record.stage_id.name}",
        'approved_by_id': f"{approval_by_usr_id}",
        'approved_by_nm': f"{approval_by_usr_nm}",
        'approval_comments': f"{approval_comment}",
        'approval_decision': f"{approval_or_reject}",
        'approval_decision_txt': f"{approval_decision_txt}",
        'approval_date_time': f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    })


class OperationContract(models.Model):
    _name = "operation.contract.contract"
    _description = "运营合同模型"

    name = fields.Char('合同名称', required=True, translate=True)
    contract_no = fields.Char(string='合同编号', readonly=True, default=lambda self: self._get_contract_no(False),
                              store=True)

    op_person_id = fields.Many2one('hr.employee', string='经办人', default=lambda self: self._get_employee())
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)

    def _get_contract_no(self, last_write):
        _logger.info("开始计算合同编号")
        if not last_write:
            return "保存时将自动获取合同号"

        prefix_rcd = self.env["operation.contract.no.prefix"].search([], limit=1)
        _logger.info(f"prefix_rcd=[{prefix_rcd}]")
        prefix_str = ""
        for rcd in prefix_rcd:
            prefix_str = rcd.prefix

        if not prefix_str:
            prefix_str = "OP-HT"

        if not prefix_str.endswith('-'):
            prefix_str = prefix_str + '-'

        _logger.info(f"prefix_str=[{prefix_str}]")

        formatted_date = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d-%H%M%S')
        random_number = '{:03d}'.format(random.randint(0, 999))
        str_ret = prefix_str + formatted_date + '-' + random_number
        _logger.info(f"str_ret=[{str_ret}]")

        return str_ret

    @api.model
    def create(self, vals):
        if (not vals.get('contract_no')) or vals.get('contract_no') == "保存时将自动获取合同号":
            vals['contract_no'] = self._get_contract_no(True)

        res = super(OperationContract, self).create(vals)

        # all_stages = self.env['operation.contract.stage'].search([])
        # # 以第一阶段创建审批明细
        # for record in res:
        #     # 新建
        #     _create_approval_detail(self, record, True, False)
        #     # 合同阶段自动推到第二个阶段
        #     i = 0
        #     for stage in all_stages:
        #         if i == 1:
        #             record.stage_sequence = stage.sequence
        #             record.stage_id = stage
        #             vals['stage_id'] = record.stage_id
        #             vals['stage_sequence'] = record.stage_sequence
        #             self.write(vals)
        #
        #         i += 1

        return res

    def write(self, vals):
        res = super(OperationContract, self).write(vals)
        return res

    def unlink(self):
        # for record in self:
        #     self.env['operation.contract.approval.detail'].search([('contract_id', '=', record.id)]).unlink()
        #     self.env['operation.contract.contract'].search([('id', '=', record.id)]).unlink()
        res = super(OperationContract, self).unlink()
        return res

    @api.model
    def _get_employee(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            return user.employee_ids[0].id  # 返回第一个employee记录ID
        else:
            return False  # 如果没有employee记录，则返回False

    @api.model
    def _get_employee_nm(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            return user.employee_ids[0].name  # 返回第一个employee记录ID
        else:
            return False  # 如果没有employee记录，则返回False

    # 使用related属性将employee_id中的某些字段映射到custom.model中
    department_id = fields.Many2one('hr.department', related='op_person_id.department_id', string="部门")
    job_title = fields.Char(related='op_person_id.job_title', string="职务")

    partner_id = fields.Many2one('res.partner', string='公司名称')
    partner_contact_id = fields.Char(string='负责人', compute='_compute_contact_info', readonly=True)
    partner_contact_phone = fields.Char(string='电话', compute='_compute_contact_info', readonly=True)
    comments = fields.Text(string="备注")

    @api.depends('partner_id')
    def _compute_contact_info(self):
        for record in self:
            # 查找partner的child_ids中is_company=False的记录，这通常代表个人联系人
            contact = record.partner_id.child_ids.filtered(lambda r: not r.is_company)
            if contact:
                record.partner_contact_id = contact[0].name
                record.partner_contact_phone = contact[0].phone
            else:
                record.partner_contact_id = False
                record.partner_contact_phone = False

    date_approval_begin = fields.Date(copy=False, string="审批发起日期", readonly=True,
                                      default=lambda self: fields.Date.context_today(self))
    date_begin = fields.Date(copy=False, string="合同开始日期")
    date_end = fields.Date(copy=False, string="合同结束日期")
    contract_amount = fields.Float(string="合同金额（元）", copy=False, default=0.0, digits=(16, 2))
    description = fields.Html(string='合同详情', store=True, readonly=False)

    def _get_default_stage_id(self):
        return self.env['operation.contract.stage'].search([], limit=1)

    stage_id = fields.Many2one(
        'operation.contract.stage', ondelete='restrict', default=_get_default_stage_id,
        group_expand='_read_group_stage_ids', copy=False)
    stage_sequence = fields.Integer(string="状态序号", related="stage_id.sequence")
    stage_op_department_id = fields.Many2one(string="状态审批部门", related="stage_id.op_department_id")
    # Kanban fields
    kanban_state = fields.Selection([('normal', '推进中'), ('done', '已完成'), ('blocked', '任务受阻')], default='normal',
                                    copy=False)
    kanban_state_label = fields.Char(
        string='看板状态', compute='_compute_kanban_state_label',
        store=True)

    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='任务受阻解释说明', readonly=True)
    legend_done = fields.Char(related='stage_id.legend_done', string='任务已完成说明', readonly=True)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='任务推进中说明', readonly=True)

    approval_detail_ids = fields.One2many('operation.contract.approval.detail', 'contract_id', string="审批情况")

    # @api.depends('contract_no')
    # def _compute_approval_details(self):
    #     for record in self:
    #         approval_details = self.env['operation.contract.approval.detail'].search(
    #             [('contract_id', '=', record.id)])
    #         for detail in approval_details:
    #             _logger.info(f"detail.approval_decision={detail.approval_decision}")
    #             _logger.info(f"detail.approval_by_id={detail.approved_by_id}")
    #             if detail.approval_decision:
    #                 detail.approval_decision_txt = "同意"
    #             elif detail.approval_date_time:  # 有操作时间
    #                 detail.approval_decision_txt = "驳回"
    #             else:
    #                 detail.approval_decision_txt = ""
    #
    #         record.approval_detail_ids = approval_details

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for event in self:
            if event.kanban_state == 'normal':
                event.kanban_state_label = event.stage_id.legend_normal
            elif event.kanban_state == 'blocked':
                event.kanban_state_label = event.stage_id.legend_blocked
            else:
                event.kanban_state_label = event.stage_id.legend_done

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['operation.contract.stage'].search([])

    @api.model
    def ondelete(self):
        for record in self:
            if record.stage_id.sequence != 0 and record.stage_id.sequence != 1000:  # 0：新建；1000：canceled
                raise UserError(_('[{0}]该条合同状态为【{1}】，不可被删除!'.format(record.name, record.stage_id)))

        return super().unlink()

    def action_agree(self):
        # 批准
        for record in self:
            # 先创建当前阶段的审批记录
            _create_approval_detail(self, record, True, False)
            all_stages = self.env['operation.contract.stage'].search([])
            for each_stage in all_stages:
                # 同意则进入下一阶段
                if each_stage.sequence > record.stage_id.sequence:
                    record.stage_sequence = each_stage.sequence
                    record.stage_id = each_stage
                    self.write({'stage_id': record.stage_id, 'stage_sequence': record.stage_sequence})
                    return

    def action_reject(self):
        # 驳回
        for record in self:
            # 先创建当前阶段的驳回记录
            _create_approval_detail(self, record, False, False)

            all_stages = self.env['operation.contract.stage'].search([])
            for each_stage in all_stages:
                if each_stage.sequence < record.stage_id.sequence:
                    tmp_stage = each_stage

                if each_stage.sequence == record.stage_id.sequence:
                    record.stage_id = tmp_stage
                    record.stage_sequence = tmp_stage.sequence
                    self.write({'stage_id': record.stage_id, 'stage_sequence': record.stage_sequence})
                    return

    def action_cancel(self):
        for record in self:
            _create_approval_detail(self, record, False, True)
            all_stages = self.env['operation.contract.stage'].search([])
            for each_stage in all_stages:
                if each_stage.sequence == 1000:
                    record.stage_id = each_stage
                    record.stage_sequence = each_stage.sequence
                    self.write({'stage_id': record.stage_id, 'stage_sequence': record.stage_sequence})
                    return

