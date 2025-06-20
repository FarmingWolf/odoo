# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random
import re
from datetime import datetime, timedelta

from addons.utils.models.utils import Utils
from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


words_to_del = ["北京市", "北京", "朝阳区", "朝阳", "豆各庄乡", "经济合作社", "有限公司"]

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    public = fields.Boolean(default=False)

class ContractExpense(models.Model):
    _name = "contract.expense"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'analytic.mixin']
    _description = "支出类合同管理"
    _order = "fund_type asc, account_subject asc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee or (not self.env.user.has_group('contract_expense.group_contract_expense_apply')
                            and not self.env.user.has_group('contract_expense.group_contract_expense_lawyer')):
            raise ValidationError(f'当前用户没有合同权限：{employee.name}')
        return employee

    @api.depends('company_id')
    def _compute_employee_id(self):
        if not self.env.context.get('default_employee_id'):
            for expense in self:
                expense.employee_id = self.env.user.with_company(expense.company_id).employee_id

    name = fields.Char("合同名称", required=True, index=True, tracking=True)
    contract_no = fields.Char("合同编号", required=True, index=True, tracking=True,
                              default=lambda self: self._get_contract_no())
    contract_amount = fields.Float("合同金额", digits=(16, 2), required=True, currency_field='company_currency_id',tracking=True)
    fund_type = fields.Many2one(comodel_name='contract.expense.fund.type', string="资金类型", required=True, tracking=True,
                                default=lambda self: self._get_fund_type())
    procurement_method = fields.Many2one(comodel_name='contract.expense.procurement.method', string="采购方式", required=True,
                                         tracking=True, default=lambda self: self._get_procurement_method())
    account_subject = fields.Many2one(comodel_name='accounting.subject.subject', string="资金科目", required=True, tracking=True)

    receiving_unit = fields.Many2one(comodel_name='res.partner', string="收款方", required=True, tracking=True,
                                     domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    receiving_bank = fields.Many2one(comodel_name="res.partner.bank", string="收款方银行", required=True, tracking=True)
    bank_account = fields.Char(string="收款方银行账号", related="receiving_bank.acc_number", required=True, tracking=True)
    payment_method = fields.Many2one(comodel_name='contract.expense.payment.method', string="支付方式", required=True,
                                     tracking=True, default=lambda self: self._get_payment_method())

    date_apply = fields.Date(string="申请日期", required=True, tracking=True, default=fields.Date.context_today)
    date_sign = fields.Date(string="签约日期", required=True, tracking=True, default=fields.Date.context_today)
    date_start = fields.Date(string="开始日期", required=True, tracking=True, default=fields.Date.context_today)
    date_end = fields.Date(string="结束日期", required=True, tracking=True, default=fields.Date.today() + timedelta(days=90))

    employee_id = fields.Many2one(comodel_name='hr.employee', string="制单人", compute='_compute_employee_id',
                                  precompute=True, store=True, readonly=False, required=True, default=_default_employee_id,
                                  check_company=True, domain=[('filter_for_contract_expense', '=', True)])
    department_id = fields.Many2one('hr.department', string="甲方", tracking=True, required=True,
                                    domain=lambda self: self._get_department_domain(),
                                    default=lambda self: self.env.user.employee_id.department_id)
    party_a_unit = fields.Char(string="甲方单位", related="department_id.name")
    company_id = fields.Many2one(comodel_name='res.company', string="公司", required=True, readonly=True,
                                 default=lambda self: self.env.company)

    company_currency_id = fields.Many2one(comodel_name='res.currency', related='company_id.currency_id',
                                          string="货币",readonly=True,)
    category_id = fields.Many2one(comodel_name='contract.expense.category', string="合同类别", tracking=True,
                                  ondelete='restrict', required=True, check_company=True,
                                  default=lambda self: self._get_default_category())

    attachment_types = fields.Many2many(related="category_id.meeting_minute_types")

    category_description = fields.Text(compute='_compute_category_description')
    state = fields.Selection(selection=[('draft', 'To Submit'), ('submitted', 'Submitted'), ('approved', 'Approved'),
                                        ('done', 'Done'), ('refused', 'Refused'), ('stopped', 'Stopped')], string="状态",
                             compute='_compute_state', store=True, readonly=True, index=True, copy=False, default='draft')

    stage = fields.Many2one('contract.expense.approval.stage', ondelete='restrict', copy=False, tracking=True,
                            default=lambda self: self._get_default_stage_id(), string="当前阶段")
    stage_sequence = fields.Integer("节点序号", related="stage.sequence")
    key_content = fields.Html(string="关键条款内容", store=True, tracking=True, required=True,
                              help="合同的关键条款内容，如：合同支付节奏、支付条件等")

    invisible_meeting_minutes = fields.Boolean(compute="_compute_invisible_meeting_minutes")
    meeting_minutes_editable = fields.Boolean(compute="_compute_meeting_minutes_editable")

    meeting_minute_help_msg = fields.Char(string="附件信息提示", compute="_compute_meeting_minute_help_msg")
    meeting_minutes_attach_link = fields.Many2many(string="会议纪要等附件链接", comodel_name='meeting.minutes',
                                                   column1='contract_expense_id', column2='meeting_minutes_id', tracking=True)

    attachment_ids = fields.One2many(comodel_name='contract.expense.attachment', string="直接上传本地附件", copy=False,
                                     tracking=True, inverse_name="contract_expense_id")

    approval_detail_ids = fields.One2many(comodel_name='contract.expense.approval.detail',
                                          inverse_name='contract_expense_id', string="审批详情")
    editable = fields.Boolean(default=True, compute='_compute_editable')

    _sql_constraints = [
        ('name', 'unique(name, company_id)', '合同名称不能重复！')
    ]

    @api.onchange('stage')
    def _onchange_stage(self):

        default_list = []
        _logger.info(f"self.stage={self.stage};self.stage.meeting_minute_types={self.stage.meeting_minute_types}")
        for default_type in self.stage.meeting_minute_types:
            default_list.append(default_type.name_show)

        if default_list:
            self.meeting_minute_help_msg = _("请上传附件 %(msg_list)s") % {'msg_list': str(default_list)}
        else:
            self.meeting_minute_help_msg = False

        self.meeting_minutes_editable = self.stage.input_meeting_minutes
        self._get_contract_no()

    @api.onchange('fund_type')
    def _onchange_fund_type(self):
        if not self.contract_no:
            self._get_contract_no()
        else:
            tmp_lst = self.contract_no.split('-')
            tmp_lst[1] = Utils.get_first_letter(self.fund_type.name)
            self.contract_no = '-'.join(tmp_lst)

    def _get_default_category(self):

        self._invalidate_cache(['stage'])

        default_ce_category_id = self.category_id.id if self.category_id else False

        if not default_ce_category_id:
            default_ce_category_id = self._get_category_from_context_session(default_ce_category_id)

        if default_ce_category_id:
            return default_ce_category_id

        if self._ids:  # 如果没有从上下文中获取到，尝试从当前记录获取
            record = self.browse(self._ids[0])
            default_ce_category_id = record.category_id.id

        if default_ce_category_id:
            return default_ce_category_id

        _logger.debug(f"record={self}")

        if not default_ce_category_id:
            default_ce_category_id = self.category_id.id

        if not default_ce_category_id:
            default_ce_category_id = self.env['contract.expense.category'].search([], limit=1).id

        if not default_ce_category_id:
            raise UserError('请先创建合同流程分类！')

        return default_ce_category_id

    @api.depends_context('lang')
    @api.depends('category_id')
    def _compute_category_description(self):
        for expense in self:
            if expense.category_id:
                expense.category_description = \
                    f"{expense.category_id.name}【{expense.category_id.amount_min}(包含)~" \
                    f"{expense.category_id.amount_max if expense.category_id.amount_max else ''}" \
                    f"{'(不包含)' if expense.category_id.amount_max else ''}】"
            else:
                expense.category_description = ''

    def _get_category_from_context_session(self, default_ce_category_id):

        if 'default_ce_category_id' in self.env.context:
            default_ce_category_id = self.env.context.get('default_ce_category_id')

        if not default_ce_category_id:
            if request and request.session and 'default_ce_category_id' in request.session:
                default_ce_category_id = request.session.get('default_ce_category_id')

        return default_ce_category_id

    @api.depends('stage')
    def _compute_meeting_minute_help_msg(self):
        for record in self:
            record._onchange_stage()

    def _compute_meeting_minutes_editable(self):
        for record in self:
            check_right, tgt_stage = self._check_approval_rights(record)
            record.meeting_minutes_editable = record.stage.input_meeting_minutes & check_right

    def _compute_invisible_meeting_minutes(self):
        for record in self:
            if record.attachment_ids or record.meeting_minutes_attach_link:
                record.invisible_meeting_minutes = False
            else:
                check_right, tgt_stage = self._check_approval_rights(record)
                if (record.stage and record.stage.input_meeting_minutes and
                        (check_right or ((record.create_uid.id or record.employee_id.user_id.id) == self.env.user.id))):
                    record.invisible_meeting_minutes = False
                else:
                    record.invisible_meeting_minutes = True

    def _compute_editable(self):
        for record in self:
            if record.state in ['submitted', 'done']:
                record.editable = False

            if record.state in ['draft', 'stopped']:
                if record.employee_id == self.env.user.employee_id:
                    record.editable = True
                else:
                    record.editable = False

            if record.state in ['approved', 'refused']:
                if record.stage.input_meeting_minutes:
                    check_right, tgt_stage = self._check_approval_rights(record)
                    if check_right:
                        record.editable = True
                    else:
                        record.editable = False
                else:
                    record.editable = False

    def _get_department_domain(self):
        domain = [('company_id', '=', self.env.user.company_id.id)]

        if not self.env.user.has_group('contract_expense.group_contract_expense_manager'):
            domain.append(('complete_name', 'ilike', str(self.env.user.employee_id.department_id.complete_name) + '%'))

        return domain

    def _get_payment_method(self):
        method = self.env['contract.expense.payment.method'].search([], limit=1).id
        if method:
            return method
        else:
            raise ValidationError('请先创建合同支付方式，如：网银转账、支票、现金等')

    def _get_fund_type(self):
        fund_type = self.env['contract.expense.fund.type'].search([], limit=1).id
        if fund_type:
            return fund_type
        else:
            raise ValidationError('请先创建资金类型定义，如：财政专项资金、集体资金等')

    def _get_procurement_method(self):
        method = self.env['contract.expense.procurement.method'].search([], limit=1).id
        if method:
            return method
        else:
            raise ValidationError('请先创建合同采购方式，如：公开招标、邀请招标、三方比价等')

    def _get_contract_no(self):

        if self.contract_no:
            return self.contract_no

        department_name = self.department_id.name
        _logger.info(f"department_name:{department_name}")
        if department_name:
            for word in words_to_del:
                department_name = department_name.replace(word, "")
            department_name_short = department_name
        else:
            return ""

        department_name_first_letter = Utils.get_first_letter(department_name_short)
        if self.fund_type and self.fund_type.name:
            fund_type_first_letter = Utils.get_first_letter(self.fund_type.name)
        else:
            return ""

        prefix_str = "HT-"
        if fund_type_first_letter:
            prefix_str = prefix_str + fund_type_first_letter

        if department_name_first_letter:
            prefix_str = prefix_str + '-' + department_name_first_letter + '-'

        formatted_date = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y%m%d-%H%M%S')
        random_number = '{:03d}'.format(random.randint(0, 999))
        str_ret = prefix_str + formatted_date + '-' + random_number
        _logger.info(f"str_ret=[{str_ret}]")
        self.contract_no = str_ret
        return str_ret

    def action_save_contract_expense(self):
        for record in self:
            if record.state != 'draft':
                record.state = 'draft'

            if not record.stage:
                default_stage = record._get_default_stage_id()
                record.stage = default_stage

            # 根据category中的meeting_minutes_type生成meeting_minutes的预备list
            for meeting_minutes_type in record.attachment_types:
                type_exists = False
                for meeting_minutes_created in record.meeting_minutes_attach_link:
                    if meeting_minutes_type == meeting_minutes_created.type:
                        type_exists = True
                        break

                for meeting_minutes_created in record.attachment_ids:
                    if meeting_minutes_type == meeting_minutes_created.type:
                        type_exists = True
                        break

                if not type_exists:
                    meeting_minutes = {
                        "contract_expense_id": record.id,
                        "type": meeting_minutes_type.id,
                    }
                    self.env["contract.expense.attachment"].create(meeting_minutes)

        return

    def _get_default_stage_id(self):
        _logger.info(f"self.env.context={self.env.context}")
        default_ce_category_id = None
        if "default_ce_category_id" in self.env.context:
            default_ce_category_id = self.env.context.get('default_ce_category_id')

        if not default_ce_category_id:
            for record in self:
                default_ce_category_id = record.category_id.id

        if not default_ce_category_id:
            default_ce_category_id = self.category_id.id
            _logger.info(f"self.category_id={default_ce_category_id}")

        if not default_ce_category_id:
            _logger.error("default_ce_category_id is None!!! Choose the 1st record!")
            default_ce_category_id = self.env['contract.expense.category'].search([],limit=1).id
            if not default_ce_category_id:
                raise ValidationError('请先创建合同流程分类')

        stage_id = self.env['contract.expense.approval.stage'].search([('company_id', '=', self.env.user.company_id.id),
                                                                       ('category_id', '=', default_ce_category_id)],
                                                                       limit=1).id
        if stage_id:
            return stage_id
        else:
            _logger.error("can't get default stage!!!")
            raise UserError('请先完成合同流程的创建并设置节点')

    def action_submit_contract_expense(self):
        self.action_save_contract_expense()
        self.action_agree('', from_action_submit=True)
        if self.date_apply != fields.Date.context_today(self):
            self.date_apply = fields.Date.context_today(self)

    def action_agree_confirm(self, context):
        _logger.info(f"context={context}")
        res_id = context.get('active_id')
        comment = context.get('comment')
        self_rcd = self.search([('id', '=', res_id)])
        self_rcd.action_agree(comment)

    def action_agree(self, comment, from_action_submit=False):
        # 批准
        for record in self:
            check_right, tgt_stage = self._check_approval_rights(record)
            _logger.debug(f"tgt_stage={tgt_stage.name};tgt_stage.seq={tgt_stage.sequence}")
            if not check_right:
                raise UserError(_("你不能处理这个节点: %(stage_name)s") % {'stage_name': record.stage.name})

            # 先检查本节点是否已经审批通过，若已通过则不用再次创建审批记录
            stage_approved, approval_decision, next_stage_lst = \
                self._check_multi_stage_approved(record, tgt_stage)

            for next_stage in next_stage_lst:
                _logger.debug(f"next_stage={next_stage['stage'].name};result={next_stage['stage_result']}")

            # 下节点通过的情况下，由于权限问题，原则上到不了这里；
            # 如果下节点驳回的情况下，由于按钮不显示也到不了这里；但是如果本节点要求上传附件，则即使下节点驳回，这里可能上传附件再提交
            for next_stage in next_stage_lst:
                if next_stage["stage_result"] is not None:
                    if not next_stage["stage_result"]:
                        if not from_action_submit:
                            if not record.stage.input_meeting_minutes:
                                raise UserError(_("This application has been rejected at stage [%(stage_name)s], "
                                                  "Please reject it !") % {'stage_name': next_stage['stage'].name})

            can_approve_again = False
            if stage_approved:
                # 如果来自下个节点的驳回，而且本节点允许上传附件，那么可以继续提交
                for next_stage in next_stage_lst:
                    if next_stage["stage_result"] is not None:
                        if not next_stage["stage_result"]:
                            if record.stage.input_meeting_minutes:
                                can_approve_again = True
                                break

            if stage_approved and not can_approve_again:
                err_msg = _("approved") if approval_decision else _("rejected")
                raise UserError(_("You have %(err_msg)s this application, "
                                  "and you can not approve it again!") % {'err_msg': err_msg})

            # 判断必传附件是否上传
            self._check_attach_mandatory()

            next_state = 'submitted' if record.stage.sequence == 0 else 'approved'
            # 先创建当前阶段的审批记录
            self._create_approval_detail(record, True, False, tgt_stage, comment)

            # 如果本阶段有多个同级别的审批节点，那么所有节点都通过后才可进入下一阶段
            same_level_approval_result = self._check_same_level_approval_result(record, tgt_stage)
            if not same_level_approval_result:
                _logger.debug("状态审批中，但是因同级别审批节点尚未完全通过，所以暂不推进本审批流的阶段")
                self.write({'state': next_state})
                return

            all_stages = self.env['contract.expense.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            (
                                                                                'category_id', '=',
                                                                                record.category_id.id)])

            max_stage_sequence = 0
            for each_stage in all_stages:
                max_stage_sequence = each_stage.sequence

            for each_stage in all_stages:
                # 从初始阶段到倒数第二个阶段都会进入此逻辑，而最后一个阶段的待审批不进入此逻辑
                # 同意则进入下一阶段
                if each_stage.sequence > record.stage.sequence:
                    record.stage = each_stage
                    if max_stage_sequence == record.stage.sequence:
                        next_state = 'done'

                    self.write({'stage': record.stage,
                                'state': next_state})
                    # 这里就应该是return，而不是break
                    return

    def action_reject_confirm(self, context):
        _logger.info(f"context={context}")
        res_id = context.get('active_id')
        comment = context.get('comment')
        self_rcd = self.search([('id', '=', res_id)])
        self_rcd.action_reject(comment)

    def action_reject(self, comment):
        # 驳回
        for record in self:
            if not record.stage.sequence:
                return

            check_right, tgt_stage = self._check_approval_rights(record)
            if not check_right:
                raise UserError(_("You can not process this stage: %(stage_name)s") % {'stage_name': record.stage.name})

            # 先检查一下本节点是否已经审批通过，若已通过则不用再次创建审批记录
            stage_approved, approval_decision, next_stage_lst = \
                self._check_multi_stage_approved(record, tgt_stage)

            # 下节点全部通过的情况下，由于权限问题，原则上到不了这里；
            # 如果下阶段平行节点有驳回的情况下，这里可以继续驳回；而下阶段的平行节点中没有驳回则不能操作
            can_approve_again = False
            if stage_approved:
                for next_stage in next_stage_lst:
                    if next_stage["stage_result"] is not None:
                        if not next_stage["stage_result"]:
                            can_approve_again = True
                            break

            if stage_approved and not can_approve_again:
                err_msg = _("approved") if approval_decision else _("rejected")
                raise UserError(_("You have %(err_msg)s this application, "
                                  "and you can not reject it again!") % {'err_msg': err_msg})

            # 先创建当前阶段的驳回记录
            self._create_approval_detail(record, False, False, tgt_stage, comment)

            all_stages = self.env['contract.expense.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            (
                                                                                'category_id', '=',
                                                                                record.category_id.id)])
            for each_stage in all_stages:
                if each_stage.sequence < record.stage.sequence:
                    tmp_stage = each_stage

                if each_stage.sequence == record.stage.sequence:
                    record.stage = tmp_stage
                    self.write({'stage': record.stage, 'state': 'refused'})
                    return

    def action_cancel(self):
        for record in self:

            if not record.stage.sequence:
                return

            check_right, tgt_stage = self._check_approval_rights(record)
            if not check_right:
                raise UserError(_("You can not process this stage: %(stage_name)s") % {'stage_name': record.stage.name})

            # 先检查一下本节点是否已经审批通过，若已通过则不用再次创建审批记录
            stage_approved, approval_decision, next_stage_lst = \
                self._check_multi_stage_approved(record, tgt_stage)

            if stage_approved:
                err_msg = _("approved") if approval_decision else _("rejected")
                raise UserError(_("You have %(err_msg)s this application, "
                                  "and you can not cancel it again!") % {'err_msg': err_msg})

            self._create_approval_detail(record, False, True, tgt_stage, comment=None)
            all_stages = self.env['contract.expense.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            (
                                                                                'category_id', '=',
                                                                                record.category_id.id)])
            for each_stage in all_stages:
                if each_stage.sequence == 1000:
                    record.stage = each_stage
                    self.write({'stage': record.stage})
                    return

    def action_stop_confirm(self, context):
        _logger.info(f"context={context}")
        res_id = context.get('active_id')
        comment = context.get('comment')
        self_rcd = self.search([('id', '=', res_id)])
        self_rcd.action_stop(comment)

    def action_stop(self, comment):
        # 一键叫停
        for record in self:
            # 理论上一键叫停对象流程已经提交
            if not record.stage.sequence:
                return

            check_right, tgt_stage = self._check_stop_rights(record)
            if not check_right:
                raise UserError(_("当前状态: %(state_name)s。 您不能处理这个节点: %(stage_name)s") %
                                {'state_name': record.state, 'stage_name': record.stage.name})

            # 先创建当前阶段的一键叫停记录
            self._create_approval_detail(record, False, False, tgt_stage, comment, is_stop=True)
            # 更新本记录：stopped，并将stage置为初始stage
            all_stages = self.env['contract.expense.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            ('category_id', '=', record.category_id.id),
                                                                            ('sequence', '=', 0)])
            for each_stage in all_stages:
                if each_stage.sequence == 0:
                    record.stage = each_stage
                    self.write({'stage': record.stage, 'state': 'stopped'})
                    return

    def _check_approval_rights(self, record):

        this_employee_dep_id = self._get_employee().department_id.id
        this_employee_job_id = self._get_employee().job_id.id

        if not record.stage:
            default_stage = record._get_default_stage_id()
            record.stage = default_stage
            _logger.error(f"record.stage is None, set it as {default_stage}")

        if not self.env.user.has_group('contract_expense.group_contract_expense_user'):
            _logger.info(f"self.env.user:{self.env.user.name}没有contract_expense.group_contract_expense_user权限")
            if not self.env.user.has_group('contract_expense.group_contract_expense_lawyer'):
                _logger.info(f"也没有contract_expense.group_contract_expense_lawyer权限")
                if not self.env.user.has_group('contract_expense.group_contract_expense_apply'):
                    _logger.info(f"也没有contract_expense.group_contract_expense_apply权限")
                    return False, record.stage
                else:
                    if record.employee_id != self.env.user.employee_id:
                        return False, record.stage
                    else:
                        if not record.stage.input_meeting_minutes:
                            return False, record.stage

        # 由于在stage创建时，对非起始stage（sequence!=0）时的部门或职位角色不同时为空做了要求
        if not record.stage.op_department_id:
            if not record.stage.op_job_id:
                _logger.info(f"record.stage={record.stage.name}不要求部门和职位角色")
                return True, record.stage
            else:
                if this_employee_job_id == record.stage.op_job_id.id or \
                        self._get_employee().job_id.name == record.stage.op_job_id.name:
                    _logger.info(f"record.stage={record.stage.name}不要求部门，只要求职位角色")
                    # 不要求部门时，为防止越级提前审批，需要保障提交人与审批人在同一部门，或者提交人所在部门的管理者是审批人
                    if (record.employee_id.department_id.id == this_employee_dep_id or
                            record.employee_id.department_id.manager_id.id == self.env.user.employee_id.id):
                        return True, record.stage

                    # 此外，由于发起者不同而导致同一category的流程由不同审批者处理的情况，需判断发起人与审批人是否在同一条部门路径上
                    # 这种情况下的避免跨级审批的逻辑校验由不同节点的审批者的job_id不同来实现
                    if (self._get_employee().department_id.complete_name and
                            self._get_employee().department_id.complete_name in record.employee_id.department_id.complete_name):
                        return True, record.stage
                    _logger.info(f"但是当前用户部门:{this_employee_dep_id}不同于提交者部门:{record.employee_id.department_id.id}，"
                                 f"当前用户employee:{self.env.user.employee_id.id}也不是其部门管理员。")
                else:
                    _logger.info(f"职位不一致:this_employee_job_id={this_employee_job_id}"
                                 f"name={self._get_employee().job_id.name};"
                                 f"record.stage.op_job_id.id={record.stage.op_job_id.id}"
                                 f"name={record.stage.op_job_id.name};")
                    # 暂时不返回，后边可能判断同级别节点
                    # return False, record.stage
        else:
            if not record.stage.op_job_id:
                if record.stage.op_department_id == this_employee_dep_id:
                    return True, record.stage
                else:
                    _logger.info(f"record.stage.op_department_id={record.stage.op_department_id};"
                                 f"this_employee_dep_id={this_employee_dep_id}")
                    # 暂时不返回，后边可能判断同级别节点
                    # return False, record.stage

        record_stage_dep_id = record.stage.op_department_id.id
        record_stage_job_id = record.stage.op_job_id.id

        if this_employee_dep_id == record_stage_dep_id and record_stage_job_id == this_employee_job_id:
            return True, record.stage
        else:
            # 有可能是同级别中的平行节点，直到找到本用户对应的节点
            for same_level_stage in record.category_id.approval_stages:
                if same_level_stage.sequence == record.stage.sequence:
                    if not same_level_stage.op_department_id:
                        if not same_level_stage.op_job_id:
                            _logger.info(f"同级别节点：{same_level_stage}不要求部门和职位角色")
                            return True, same_level_stage
                        else:
                            if same_level_stage.op_job_id.id == this_employee_job_id or \
                                    same_level_stage.op_job_id.name == self._get_employee().job_id.name:
                                _logger.info(f"同级别节点：{same_level_stage.op_job_id.name}仅要求职位角色")
                                # 不要求部门只要求角色时，为防止高级别跨级提前审批
                                if (record.employee_id.department_id.id == this_employee_dep_id or
                                        record.employee_id.department_id.manager_id.id == self.env.user.employee_id.id):
                                    return True, same_level_stage
                                # 此外，由于发起者不同而导致同一category的流程由不同审批者处理的情况，需判断发起人与审批人是否在同一条部门路径上
                                # 这种情况下的避免跨级审批的逻辑校验由不同节点的审批者的job_id不同来实现
                                if (self._get_employee().department_id.complete_name and
                                        self._get_employee().department_id.complete_name in record.employee_id.department_id.complete_name):
                                    return True, same_level_stage
                                _logger.info(f"但是当前用户部门:{this_employee_dep_id}不同于提交者部门:{record.employee_id.department_id.id}，"
                                             f"当前用户employee:{self.env.user.employee_id.id}也不是其部门管理员。")
                    else:
                        if same_level_stage.op_department_id.id == this_employee_dep_id:
                            if not same_level_stage.op_job_id:
                                _logger.info(f"同级别节点：{same_level_stage.op_department_id.name}仅要求部门")
                                return True, same_level_stage
                            else:
                                if same_level_stage.op_job_id.id == this_employee_job_id or \
                                        same_level_stage.op_job_id.name == self._get_employee().job_id.name:
                                    _logger.info(f"同级别节点：{same_level_stage}部门和职位角色符合要求")
                                    return True, same_level_stage
            _logger.info(f"同级别节点中无符合要求的节点，或无同级别节点")
            return False, record.stage

    def _check_multi_stage_approved(self, record, tgt_stage):
        """
        第一个返回值：最新一轮审批中是否存在本节点的审批记录
        第二个返回值：最新一轮审批中本节点的审批记录的审批结果
        第三个返回值：最新一轮审批中本节点的下一个节点，即领导节点的[(节点，审批结果)]，可能是平行多节点
        """
        approval_exists = None
        approval_result = None
        next_stage_lst = []

        for each_stage in record.category_id.approval_stages:
            if each_stage.sequence > tgt_stage.sequence:
                next_stage = each_stage
                if next_stage_lst:
                    if next_stage_lst[0]['stage'].sequence == next_stage.sequence:
                        next_stage_lst.append({'stage': next_stage, 'stage_result': None})
                else:
                    next_stage_lst.append({'stage': next_stage, 'stage_result': None})

        tgt_model = 'contract.expense.approval.detail'
        domain = [('contract_expense_id', '=', record.id)]
        rcds = self.env[tgt_model].search(domain, order="id DESC")
        for rcd in rcds:
            _logger.debug(
                f"rcd.id={rcd.id}approval_stage_nm={rcd.approval_stage_nm};stage={rcd.approval_stage};"
                f"stage.id={rcd.approval_stage.id};stage.nm={rcd.approval_stage.name}")
            # 仅检查最新一轮提交
            if rcd.approval_stage.sequence == 0:
                break

            # 如果找到了驳回后的补充信息再提交阶段，也不继续往前找了
            if tgt_stage.sequence > rcd.approval_stage.sequence:
                if rcd.approval_stage.input_meeting_minutes:
                    if rcd.approval_decision:
                        break

            if rcd.approval_stage_id == tgt_stage.id:
                approval_exists = True
                approval_result = rcd.approval_decision
                break

        for next_stage in next_stage_lst:
            # 如果当前stage.sequence比可补充信息的stage.sequence大，且可补充信息的stage已经存在“通过”的日志，那么当前stage只检查到此为止
            for rcd in rcds:
                if rcd.approval_stage.sequence == 0:
                    break

                if next_stage['stage'].sequence > rcd.approval_stage.sequence:
                    if rcd.approval_stage.input_meeting_minutes:
                        if rcd.approval_decision:
                            break

                if rcd.approval_stage_id == next_stage['stage'].id:
                    _logger.debug(
                        f"next_stage={next_stage['stage'].name}的result设置为{rcd.approval_decision}rcd.id={rcd.id}")
                    next_stage['stage_result'] = rcd.approval_decision
                    break

        return approval_exists, approval_result, next_stage_lst

    def _check_same_level_approval_result(self, record, tgt_stage):

        approval_details = self.env['contract.expense.approval.detail'].search([('contract_expense_id', '=', record.id)],
                                                                              order="id DESC")
        rst = []
        # 仅找最新提交以来的
        for stage in record.category_id.approval_stages:
            # 本节点的审批记录数据，由于刚插入，现在取出来还有若干字段值为空，那么，既然来自action_agree的调用，所以直接跳过本节点
            if stage.id == tgt_stage.id:
                _logger.debug(f"tgt_stage={tgt_stage.name}；添加{stage.name}并强制设result为true")
                rst.append([stage, True])
                continue

            _logger.debug(
                f"stage={stage.name};sequence={stage.sequence}=record.stage.sequence?{record.stage.sequence == stage.sequence}")
            # 其他和本stage相同sequence的平行节点
            if stage.sequence == record.stage.sequence:
                approved = False
                for rcd in approval_details:
                    _logger.debug(
                        f"rcd.id={rcd.id}approval_stage_nm={rcd.approval_stage_nm};stage={rcd.approval_stage};"
                        f"stage.id={rcd.approval_stage.id};stage.nm={rcd.approval_stage.name}")
                    if rcd.approval_stage_nm != rcd.approval_stage.name:
                        # 经确认，刚创建的detail记录中部分字段为空
                        continue

                    # 驳回到头再提交之前的不看
                    if rcd.approval_stage.sequence == 0:
                        _logger.debug(f"到头了")
                        approved = False
                        break

                    # 已经找到了【添加附件节点已通过】表示修改了附件或其他信息再提交了，就不能再往前找该stage的驳回记录了
                    if stage.sequence > rcd.approval_stage.sequence:
                        if rcd.approval_stage.input_meeting_minutes:
                            if rcd.approval_decision:
                                _logger.debug(f"stage={stage.name}强制设result为False")
                                approved = False
                                break

                    if stage.id == rcd.approval_stage_id:
                        _logger.debug(f"stage={stage.name}设result为{rcd.approval_decision}")
                        rst.append([stage, rcd.approval_decision])
                        approved = True
                        break

                if not approved:
                    _logger.debug(f"stage={stage.name}被迫设result为False")
                    rst.append([stage, False])
            else:
                continue

        # 如果同级别的节点，任意一个没有审批通过，则视为本级别未通过
        for each_stage in rst:
            _logger.debug(f"rst.each_stage={each_stage[0].name};result={each_stage[1]}")
            if not each_stage[1]:
                # 来自action_agree，所以本级别认为已通过
                if each_stage[0].id == tgt_stage.id:
                    continue
                _logger.debug(f"stage{each_stage[0].name}尚未审批通过")
                return False

        return True
    
    def _check_stop_rights(self, record):
        if not record.stage:
            default_stage = record._get_default_stage_id()
            record.stage = default_stage
            _logger.error(f"record.stage is None, set it as {default_stage}")

        if not self.env.user.has_group('contract_expense.group_contract_expense_advanced_user'):
            _logger.info(f"self.env.user:{self.env.user.name}没有contract_expense.group_contract_expense_advanced_user")
            return False, record.stage

        # 任何没有完成审批的流程都可以一键叫停
        if record.state in ['draft', 'done', 'stopped']:
            return False, record.stage

        _logger.info(f"可以一键叫停, 当前 state={record.state}, stage={record.stage}")
        return True, record.stage

    def _create_approval_detail(self, record, approval_or_reject, is_cancel, tgt_stage, comment, is_stop=False):

        _logger.debug(f"datetime.now()[{datetime.now()}]")
        date_time = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        _logger.debug(f"date:{date_time}")

        this_user = self._get_employee()
        approval_by_usr_id = this_user.id
        approval_by_usr_nm = this_user.name

        if approval_or_reject:
            approval_decision_txt = "同意"
            approval_comment = comment if comment else "同意"
        else:
            approval_decision_txt = "驳回"
            approval_comment = comment if comment else "驳回"

        if is_stop:
            approval_decision_txt = "一键叫停"
            approval_comment = comment if comment else "一键叫停"

        if record.stage.sequence == 0:
            rcd_exists = self.env['contract.expense.approval.detail'].browse(
                record.approval_detail_ids.ids).exists()

            if rcd_exists:
                approval_comment = comment if comment else "再提交"
            else:
                approval_comment = comment if comment else "新建"

        if is_cancel:
            approval_decision_txt = "取消"
            approval_comment = comment if comment else "取消"

        _logger.debug(f"创建审批记录approval_or_reject={approval_or_reject}")
        self.env['contract.expense.approval.detail'].create({
            'contract_expense_id': f"{record.id}",
            'approval_stage': f"{tgt_stage.id}",
            'approval_stage_id': f"{tgt_stage.id}",
            'approval_stage_nm': f"{tgt_stage.name}",
            'approved_by_id': f"{approval_by_usr_id}",
            'approved_by_nm': f"{approval_by_usr_nm}",
            'approval_comments': f"{approval_comment}",
            'approval_decision': approval_or_reject,
            'approval_decision_txt': f"{approval_decision_txt}",
            'approval_date_time': f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        })

    @api.model
    def _get_employee(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            # 返回第一个employee记录ID
            # first_user = user.employee_ids[0]
            # return first_user.id, first_user.name, first_user.department_id, first_user.job_id
            return user.employee_ids[0]
        else:
            return False  # 如果没有employee记录，则返回False

    def _check_attach_mandatory(self):
        for rcd in self:
            err_lst = []
            _logger.info(f"rcd.stage.meeting_minute_types={rcd.stage.meeting_minute_types}")
            for m_m_type in rcd.stage.meeting_minute_types:
                if not m_m_type.mandatory:
                    continue

                type_exists = False
                _logger.info(f"rcd.meeting_minutes_attach={rcd.meeting_minutes_attach_link}")
                for meeting_minutes_created in rcd.meeting_minutes_attach_link:
                    if m_m_type == meeting_minutes_created.type and meeting_minutes_created.nb_attachment > 0:
                        type_exists = True
                        break
                _logger.info(f"type_exists in meeting_minutes_attach_link={type_exists}")
                for attachment in rcd.attachment_ids:
                    if m_m_type == attachment.type and attachment.nb_attachment > 0:
                        type_exists = True
                        break

                if not type_exists:
                    err_lst.append(m_m_type.name)

            _logger.info(f"err_lst={err_lst}")
            if err_lst:
                msg_attach = ""
                if rcd.stage_sequence > 0:
                    msg_attach = "如果您是律师，请点击【直接上传本地附件】"
                raise UserError(_("本阶段 [%(stage_name)s] 有必须上传的附件而未上传:%(err_lst)s。%(msg_attach)s") %
                                {'stage_name': rcd.stage.name, 'err_lst': err_lst, 'msg_attach': msg_attach})

    def _is_amount_in_category(self):
        for record in self:
            comp_tgt = record.contract_amount

            if comp_tgt == 0:
                return False

            if record.category_id.amount_max:
                if record.category_id.amount_min <= comp_tgt < record.category_id.amount_max:
                    return True
                else:
                    return False
            else:
                if record.category_id.amount_min <= comp_tgt:
                    return True
                else:
                    return False
        return True

    def _record_check(self):
        for rcd in self:
            if not rcd._is_amount_in_category():
                # 判断是否是为合同类支付，如果是提示Contract合同金额应在类别金额范围内，
                raise UserError(_("合同金额应在合同类别规定的金额范围内！"))


    @api.model
    def create(self, vals):
        res = super().create(vals)
        res._record_check()
        return res

    def write(self, vals):
        ret = super().write(vals)
        self._record_check()

        return ret