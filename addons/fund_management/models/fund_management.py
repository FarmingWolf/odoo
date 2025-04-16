# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
from datetime import datetime
from xml import etree

from markupsafe import Markup
import werkzeug

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools.misc import format_date
from odoo.tools import email_split, float_repr, float_round, is_html_empty

_logger = logging.getLogger(__name__)


class FundManagement(models.Model):
    _name = "fund.management"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'analytic.mixin']
    _description = "Fund Management"
    _order = "date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee and not self.env.user.has_group('fund_management.group_fund_management_team_approve'):
            raise ValidationError(_('The current user has no related employee. Please, create one.'))
        return employee

    name = fields.Char(
        string="Description",
        compute='_compute_name', precompute=True, store=True, readonly=False,
        required=True,
        copy=True,
        tracking=True
    )
    date = fields.Date(string="Apply Date", default=fields.Date.context_today, tracking=True)
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Applicant",
        compute='_compute_employee_id', precompute=True, store=True, readonly=False,
        required=True,
        default=_default_employee_id,
        check_company=True,
        domain=[('filter_for_fund_management', '=', True)],
        tracking=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    def _get_category_from_context_session(self, default_category_id):

        if 'default_category_id' in self.env.context:
            default_category_id = self.env.context.get('default_category_id')

        if not default_category_id:
            if request and request.session and 'default_category_id' in request.session:
                default_category_id = request.session.get('default_category_id')

        return default_category_id

    def _get_default_category(self):

        self._invalidate_cache(['stage'])

        default_category_id = self.category_id.id if self.category_id else False

        if not default_category_id:
            default_category_id = self._get_category_from_context_session(default_category_id)

        if default_category_id:
            return default_category_id

        if self._ids:  # 如果没有从上下文中获取到，尝试从当前记录获取
            record = self.browse(self._ids[0])
            default_category_id = record.category_id.id

        if default_category_id:
            return default_category_id

        for record in self:
            _logger.debug(f"record={record}")

            if not default_category_id:
                default_category_id = record.category_id.id

            if not default_category_id:
                default_category_id = record._get_category_from_context_session(default_category_id)

            if default_category_id:
                return default_category_id

        return default_category_id

    category_id = fields.Many2one(
        comodel_name='fund.management.category',
        string="Category",
        tracking=True,
        check_company=True,
        ondelete='restrict',
        required=True,
        default=lambda self: self._get_default_category()
    )
    category_description = fields.Text(compute='_compute_category_description')

    description = fields.Text(string="Notes", tracking=True)
    nb_attachment = fields.Integer(string="Number of Attachments", compute='_compute_nb_attachment')
    attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        domain="[('res_model', '=', 'fund.management')]",
        string="Attachments", tracking=True
    )
    state = fields.Selection(
        selection=[
            ('draft', 'To Submit'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('refused', 'Refused')
        ],
        string="Status",
        compute='_compute_state', store=True, readonly=True,
        index=True,
        copy=False,
        default='draft',
    )

    meeting_minutes_editable = fields.Boolean("Meeting Minutes Editable", related="stage.input_meeting_minutes")
    meeting_minute_types = fields.Many2many(string="Meeting Minute Types", related="category_id.meeting_minute_types")

    meeting_minutes_attach = fields.One2many(string="Meeting minutes attachment", inverse_name="fund_management_id",
                                             comodel_name="fund.management.meeting.minutes")

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        default_category_id = self._get_default_category()

        _logger.debug(f"进入_get_view default_category_id={default_category_id}")

        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form':
            stage_node = next(iter(arch.xpath('//field[@name="stage"]')), None)
            if stage_node is not None:
                stage_node.attrib['domain'] = f"[('company_id', '=', company_id), " \
                                              f"('category_id', '=', {default_category_id})]"

        return arch, view

    def _get_stage_domain(self):

        default_category_id = self._get_default_category()
        _logger.debug(f"default_category_id={default_category_id}")
        _logger.debug(f"active_id={self.env.context.get('active_id')}")
        stage_domain = [('company_id', '=', self.env.user.company_id.id), ('category_id', '=', default_category_id)]

        _logger.debug(f"stage_domain={stage_domain}")
        self._get_view()
        return stage_domain

    stage = fields.Many2one('fund.management.approval.stage', ondelete='restrict', copy=False, tracking=True,
                            domain=lambda self: self._get_stage_domain(),
                            default=lambda self: self._get_default_stage_id())
    stage_sequence = fields.Integer("Approval Stage Sequence NO.", related="stage.sequence")
    contract_no = fields.Char(string='Contract NO.', tracking=True, )
    contract_name = fields.Char(string='Contract Name', tracking=True, )
    contract_amount = fields.Float(string="Contract Total Amount", tracking=True, required=True)
    party_b_id = fields.Many2one('res.partner', string='Payee', index=True, copy=True, tracking=True,
                                 domain="[('company_id', '=', company_id)]")
    # Amount fields
    total_amount_currency = fields.Monetary(
        string="Apply In Currency",
        currency_field='currency_id',
        store=True, readonly=False,
        tracking=True,
    )
    total_amount_currency_percent = fields.Float(
        string="Apply In Percentage",
        compute='_compute_total_amount_currency_percent', store=True, readonly=True,
        tracking=False
    )

    @api.depends('total_amount_currency', 'contract_amount')
    def _compute_total_amount_currency_percent(self):
        for record in self:
            if record.contract_amount:
                record.total_amount_currency_percent = record.total_amount_currency / record.contract_amount
            else:
                record.total_amount_currency_percent = 0

    total_amt_cur_hist_accu = fields.Monetary(
        string="Historically Accumulation In Currency",
        currency_field='currency_id',
        store=True, readonly=False,
        tracking=True,
    )

    total_amt_cur_hist_accu_percent = fields.Float(
        string="Historically Accumulation In Percentage",
        compute='_compute_total_amt_cur_hist_accu_per', store=True, readonly=True,
        tracking=False
    )

    @api.depends('total_amt_cur_hist_accu', 'contract_amount')
    def _compute_total_amt_cur_hist_accu_per(self):
        for record in self:
            if record.contract_amount:
                record.total_amt_cur_hist_accu_percent = record.total_amt_cur_hist_accu / record.contract_amount
            else:
                record.total_amt_cur_hist_accu_percent = 0

    total_amount = fields.Monetary(
        string="Total",
        currency_field='company_currency_id',
        compute='_compute_total_amount', precompute=True, store=True, readonly=False,
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        compute='_compute_currency_id', precompute=True, store=True, readonly=False,
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Report Company Currency",
        readonly=True,
    )
    is_multiple_currency = fields.Boolean(
        string="Is currency_id different from the company_currency_id",
        compute='_compute_is_multiple_currency',
    )

    # Security fields
    is_editable = fields.Boolean(string="Is Editable By Current User", compute='_compute_is_editable', default=True)

    approval_detail_ids = fields.One2many(comodel_name='fund.management.approval.detail',
                                          inverse_name='fund_management_id', string="Approval Details")

    @api.onchange("category_id")
    def _onchange_category_id(self):
        stage_ids = self.env['fund.management.approval.stage'].search([('company_id', '=', self.env.user.company_id.id),
                                                                       ('category_id', '=', self.category_id.id)],
                                                                      limit=1)

        _logger.debug(f"stage_ids={stage_ids}")
        if stage_ids:
            self.stage = stage_ids[0]

        if self.category_id.id:
            if request and request.session:
                request.session['default_category_id'] = self.category_id.id
        # 强制刷新
        self._get_view()

    def _compute_is_editable(self):
        for record in self:
            if record.state == "draft":
                record.is_editable = True
            else:
                if record.stage and record.stage.input_meeting_minutes:
                    record.is_editable = True
                else:
                    record.is_editable = False

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

    @api.depends('category_id')
    def _compute_name(self):
        for expense in self:
            expense.name = expense.name or expense.category_description

    @api.depends('currency_id', 'company_currency_id')
    def _compute_is_multiple_currency(self):
        for expense in self:
            expense.is_multiple_currency = expense.currency_id != expense.company_currency_id

    @api.depends(
        'date',
        'company_id',
        'currency_id',
        'company_currency_id',
        'is_multiple_currency',
        'total_amount_currency',
        'category_id',
        'employee_id.user_id.partner_id',
    )
    def _compute_total_amount(self):
        for expense in self:
            expense.total_amount = expense.total_amount_currency

    @api.depends('company_id')
    def _compute_employee_id(self):
        if not self.env.context.get('default_employee_id'):
            for expense in self:
                expense.employee_id = self.env.user.with_company(expense.company_id).employee_id

    @api.depends('meeting_minutes_attach')
    def _compute_nb_attachment(self):
        for record in self:
            tmp_cnt = 0
            for meeting_minutes in record.meeting_minutes_attach:
                tmp_cnt += meeting_minutes.nb_attachment
            record.nb_attachment = tmp_cnt

    def attach_document(self, **kwargs):
        """When an attachment is uploaded as a receipt, set it as the main attachment."""
        self.message_main_attachment_id = kwargs['attachment_ids'][-1]

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_approved(self):
        for expense in self:
            if expense.state in {'done', 'approved'}:
                raise UserError(_('You cannot delete a posted or approved fund management application.'))

    @api.model
    def write(self, vals):
        if 'tax_ids' in vals:
            if any(not expense.is_editable for expense in self):
                raise UserError(_('You are not authorized to edit this fund management application.'))
        res = super().write(vals)

        return res

    def unlink(self):
        attachments_to_unlink = self.env['ir.attachment']
        checksums = set(self.attachment_ids.mapped('checksum'))
        attachments_to_unlink += self.attachment_ids.filtered(lambda att: att.checksum in checksums)
        attachments_to_unlink.with_context(sync_attachment=False).unlink()
        return super().unlink()

    # ----------------------------------------
    # Actions
    # ----------------------------------------
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res.update({
            'domain': [('res_model', '=', 'fund.management'), ('res_id', 'in', self.ids)],
            'context': {'default_res_model': 'fund.management', 'default_res_id': self.id},
        })
        return res

    def _get_default_stage_id(self):
        _logger.debug(f"self.env.context={self.env.context}")
        default_category_id = None
        if "default_category_id" in self.env.context:
            default_category_id = self.env.context.get('default_category_id')

        if not default_category_id:
            for record in self:
                default_category_id = record.category_id.id

        if not default_category_id:
            default_category_id = self.category_id.id
            _logger.debug(f"self.category_id={default_category_id}")

        if not default_category_id:
            _logger.error("default_category_id is None!!!")

        stage_ids = self.env['fund.management.approval.stage'].search([('company_id', '=', self.env.user.company_id.id),
                                                                       ('category_id', '=', default_category_id)],
                                                                      limit=1)
        if stage_ids:
            return stage_ids[0]
        else:
            _logger.error("can't get default stage!!!")
            return False

    def action_save_fund_management(self):
        for record in self:
            if record.state != 'draft':
                record.state = 'draft'

            if not record.stage:
                default_stage = record._get_default_stage_id()
                record.stage = default_stage

            # 根据category中的meeting_minutes_type生成meeting_minutes的预备list
            for meeting_minutes_type in record.meeting_minute_types:
                type_exists = False
                for meeting_minutes_created in record.meeting_minutes_attach:
                    if meeting_minutes_type == meeting_minutes_created.type:
                        type_exists = True
                        break
                if not type_exists:
                    meeting_minutes = {
                        "fund_management_id": record.id,
                        "type": meeting_minutes_type.id,
                    }
                    self.env["fund.management.meeting.minutes"].create(meeting_minutes)
        return

    def action_submit_fund_management(self):
        self.action_save_fund_management()
        self.action_agree('新建', from_action_submit=True)

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
                raise UserError(f"您不能审批当前阶段：{record.stage.name}")

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
                                raise UserError(f"本流程在【{next_stage['stage'].name}】已被驳回，请继续驳回本流程！")

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
                raise UserError(f"您已审批{'通过' if approval_decision else '驳回'}，不能再【同意】")

            next_state = 'submitted' if record.stage.sequence == 0 else 'approved'
            # 先创建当前阶段的审批记录
            self._create_approval_detail(record, True, False, tgt_stage, comment)

            # 如果本阶段有多个同级别的审批节点，那么所有节点都通过后才可进入下一阶段
            same_level_approval_result = self._check_same_level_approval_result(record, tgt_stage)
            if not same_level_approval_result:
                _logger.debug("状态审批中，但是因同级别审批节点尚未完全通过，所以暂不推进本审批流的阶段")
                self.write({'state': next_state})
                return

            all_stages = self.env['fund.management.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            (
                                                                            'category_id', '=', record.category_id.id)])

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
                raise UserError(f"您不能审批当前阶段：{record.stage.name}")

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
                raise UserError(f"您已审批{'通过' if approval_decision else '驳回'}，不能再【驳回】")

            # 先创建当前阶段的驳回记录
            self._create_approval_detail(record, False, False, tgt_stage, comment)

            all_stages = self.env['fund.management.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            (
                                                                            'category_id', '=', record.category_id.id)])
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
                raise UserError(f"您不能操作当前阶段：{record.stage.name}")

            # 先检查一下本节点是否已经审批通过，若已通过则不用再次创建审批记录
            stage_approved, approval_decision, next_stage_lst = \
                self._check_multi_stage_approved(record, tgt_stage)

            if stage_approved:
                raise UserError(f"您已审批{'通过' if approval_decision else '驳回'}，不能再【取消】")

            self._create_approval_detail(record, False, True, tgt_stage, comment=None)
            all_stages = self.env['fund.management.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            (
                                                                            'category_id', '=', record.category_id.id)])
            for each_stage in all_stages:
                if each_stage.sequence == 1000:
                    record.stage = each_stage
                    self.write({'stage': record.stage})
                    return

    def _check_approval_rights(self, record):

        this_employee_dep_id = self._get_employee().department_id.id
        this_employee_job_id = self._get_employee().job_id.id

        if not record.stage:
            default_stage = record._get_default_stage_id()
            record.stage = default_stage
            _logger.error(f"record.stage is None, set it as {default_stage}")

        if not self.env.user.has_group('fund_management.group_fund_management_team_approver'):
            _logger.info(f"self.env.user:{self.env.user.name}没有fund_management.group_fund_management_team_approver权限")
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
                    return True, record.stage
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
                                return True, same_level_stage
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

    def _create_approval_detail(self, record, approval_or_reject, is_cancel, tgt_stage, comment):

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

        if record.stage.sequence == 0:
            rcd_exists = self.env['fund.management.approval.detail'].browse(
                record.approval_detail_ids.ids).exists()

            if rcd_exists:
                approval_comment = comment if comment else "再提交"
            else:
                approval_comment = comment if comment else "新建"

        if is_cancel:
            approval_decision_txt = "取消"
            approval_comment = comment if comment else "取消"

        _logger.debug(f"创建审批记录approval_or_reject={approval_or_reject}")
        self.env['fund.management.approval.detail'].create({
            'fund_management_id': f"{record.id}",
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

    def get_fund_management_to_submit(self):
        # if there ere no records selected, then select all draft fund management for the user
        if self:
            expenses = self.filtered(lambda expense: expense.state == 'draft' and expense.is_editable)
        else:
            expenses = self.env['fund.management'].search([
                ('state', '=', 'draft'),
                ('employee_id', '=', self.env.user.employee_id.id),
                ('is_editable', '=', True),
            ])

        if not expenses:
            raise UserError(_('You have no fund application to report'))
        return expenses.action_save_fund_management()

    # ----------------------------------------
    # Business
    # ----------------------------------------

    @api.model
    def get_fund_management_dashboard(self):
        expense_state = {
            # 'to_submit': {
            #     'description': _('to submit'),
            #     'amount': 0.0,
            #     'tooltip': _("Fund management application that need to be submitted to the approver."),
            #     'currency': self.env.company.currency_id.id,
            # },
            'submitted': {
                'description': _('to be approved'),
                'amount': 0.0,
                'tooltip': _(
                    "Fund management application has been submitted to the approver and is waiting for approval."),
                'currency': self.env.company.currency_id.id,
            },
            'approved': {
                'description': _('approval process on going'),
                'amount': 0.0,
                'tooltip': _("Fund management application has been approved by some approvers."),
                'currency': self.env.company.currency_id.id,
            },
            'done': {
                'description': _('approval process completed'),
                'amount': 0.0,
                'tooltip': _("Fund management application has been approved by all approvers."),
                'currency': self.env.company.currency_id.id,
            }
        }
        if not self.env.user.employee_ids:
            return expense_state
        target_currency = self.env.company.currency_id
        # Counting the expenses to display in the dashboard:
        expenses = self._read_group(
            [('state', 'in', ('submitted', 'approved', 'done'))
             ], ['state'], ['total_amount:sum'])
        for state, total_amount_sum in expenses:
            # if state in {'draft'}:  # Fuse the two states into only one "To Submit" state
            #     state = 'to_submit'
            expense_state[state]['amount'] += total_amount_sum
        return expense_state

    @api.model
    def get_approval_process_stages(self, default_category_id, default_fund_management_id):
        rtn_stages = []
        if not default_category_id:
            return rtn_stages

        stage_domain = [('category_id', '=', default_category_id)]
        meta_stages = self.env['fund.management.approval.stage'].search(stage_domain)
        detail_domain = [('fund_management_id', '=', default_fund_management_id)]
        approval_details = self.env['fund.management.approval.detail'].search(detail_domain, order="id DESC")

        all_stages = []
        for stage in meta_stages:
            stage_data = {
                "stage_id": stage.id,
                "name": stage.name,
                "sequence": stage.sequence,
                "approval_decision": None,
                "approval_decision_txt": None,
                "pipe_end": stage.pipe_end,
                "op_department": stage.op_department_id.name,
                "op_job": stage.op_job_id.name,
            }
            # 从审批明细中倒序找到stage的审批结果通过与否
            for detail in approval_details:
                if stage.id == detail.approval_stage.id:
                    stage_data['approval_decision'] = detail.approval_decision
                    stage_data['approval_decision_txt'] = detail.approval_decision_txt
                    break
                # 若流程曾经被驳回，那么只看到最新提交之后的
                if detail.approval_stage.sequence == 0:
                    break

                # 若流程被驳回，又在添加其他信息阶段再提交了，那么只看到这个再提交
                if stage.sequence > detail.approval_stage.sequence:
                    if detail.approval_stage.input_meeting_minutes:
                        if detail.approval_decision:
                            break

            all_stages.append(stage_data)

        # 如果流程全部结束，那么为了设置最后一个阶段颜色，需要将最后一个阶段的approval_decision = True
        stage_len = len(all_stages)
        if stage_len > 1:
            all_stages[stage_len - 1]['approval_decision'] = all_stages[stage_len - 2]['approval_decision']

        # 在被驳回的流程中，从第二个阶段驳回到第一个阶段时，第一个阶段本是已提交状态，但是应该是编辑中待提交状态更合理
        if stage_len > 1:
            if all_stages[1]['approval_decision'] is not None and not all_stages[1]['approval_decision']:
                all_stages[0]['approval_decision'] = None
            # 也有可能从第二个阶段开始就有平行级别节点
            else:
                for each_stage in all_stages:
                    if all_stages[1]['sequence'] == each_stage['sequence']:
                        if each_stage['approval_decision'] is not None and not each_stage['approval_decision']:
                            all_stages[0]['approval_decision'] = None
                            break

        current_group = [all_stages[0]]  # 初始化第一个分组

        for i in range(1, stage_len):
            if all_stages[i]['sequence'] == current_group[0]['sequence']:
                current_group.append(all_stages[i])  # sequence 相同，加入当前分组
            else:
                rtn_stages.append(current_group)  # sequence 不同，提交当前分组
                current_group = [all_stages[i]]  # 开始新分组

        rtn_stages.append(current_group)  # 添加最后一个分组

        return rtn_stages

    # ----------------------------------------
    # Mail Thread
    # ----------------------------------------

    @api.model
    def _parse_price(self, expense_description, currencies):
        """ Return price, currency and updated description """
        symbols, symbols_pattern, float_pattern = [], '', r'[+-]?(\d+[.,]?\d*)'
        price = 0.0
        for currency in currencies:
            symbols += [re.escape(currency.symbol), re.escape(currency.name)]
        symbols_pattern = '|'.join(symbols)
        price_pattern = f'(({symbols_pattern})?\\s?{float_pattern}\\s?({symbols_pattern})?)'
        matches = re.findall(price_pattern, expense_description)
        currency = currencies[:1]
        if matches:
            match = max(matches, key=lambda match: len([group for group in match if group]))
            # get the longest match. e.g. "2 chairs 120$" -> the price is 120$, not 2
            full_str = match[0]
            currency_str = match[1] or match[3]
            price = match[2].replace(',', '.')

            if currency_str and currencies:
                currencies = currencies.filtered(lambda c: currency_str in [c.symbol, c.name])
                currency = currencies[:1] or currency
            expense_description = expense_description.replace(full_str, ' ')  # remove price from description
            expense_description = re.sub(' +', ' ', expense_description.strip())

        return float(price), currency, expense_description

    def fund_management_actions_open_form(self):

        self_rcd_id = self.env.context.get('self_rcd_id')

        self_rcd = self.browse(self_rcd_id)
        default_category_id = self_rcd.category_id.id
        request.session["default_category_id"] = default_category_id
        _logger.debug(f"self_rcd_id={self_rcd_id};default_category_id={default_category_id}")
        # 清理缓存
        self._invalidate_cache(['stage'])

        action = {
            "name": f"{self.name}",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "fund.management",
            "res_id": self_rcd_id,
            "context": {"default_category_id": default_category_id},
            "views": [
                (self.env.ref('fund_management.fund_management_view_form').id, 'form'),
                (False, 'form')],
        }
        return action

    def action_view_all_stages(self):

        default_category_id = self.env.context.get("default_category_id")
        _logger.debug(f"default_category_id={default_category_id}")
        action = {
            "name": f"{self.name}",
            "type": "ir.actions.act_window",
            "view_mode": "tree",
            "res_model": "fund.management.approval.stage",
            "context": {"default_category_id": default_category_id},
            "target": "new",
            "views": [
                (self.env.ref('fund_management.fund_management_approval_stage_by_category_tree').id, 'tree')],
        }
        return action

    def _check_same_level_approval_result(self, record, tgt_stage):

        approval_details = self.env['fund.management.approval.detail'].search([('fund_management_id', '=', record.id)],
                                                                              order="id DESC")
        rst = []
        # 仅找最新提交以来的
        for stage in record.category_id.approval_stages:
            # 本节点的审批记录数据，由于刚插入，现在取出来还有若干字段值为空，那么，既然来自action_agree的调用，所以直接跳过本节点
            if stage.id == tgt_stage.id:
                _logger.debug(f"tgt_stage={tgt_stage.name}；添加{stage.name}并强制设result为true")
                rst.append([stage, True])
                continue

            _logger.debug(f"stage={stage.name};sequence={stage.sequence}=record.stage.sequence?{record.stage.sequence == stage.sequence}")
            # 其他和本stage相同sequence的平行节点
            if stage.sequence == record.stage.sequence:
                approved = False
                for rcd in approval_details:
                    _logger.debug(f"rcd.id={rcd.id}approval_stage_nm={rcd.approval_stage_nm};stage={rcd.approval_stage};stage.id={rcd.approval_stage.id};stage.nm={rcd.approval_stage.name}")
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

        tgt_model = 'fund.management.approval.detail'
        domain = [('fund_management_id', '=', record.id)]
        rcds = self.env[tgt_model].search(domain, order="id DESC")
        for rcd in rcds:
            _logger.debug(f"rcd.id={rcd.id}approval_stage_nm={rcd.approval_stage_nm};stage={rcd.approval_stage};stage.id={rcd.approval_stage.id};stage.nm={rcd.approval_stage.name}")
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
                    _logger.debug(f"next_stage={next_stage['stage'].name}的result设置为{rcd.approval_decision}rcd.id={rcd.id}")
                    next_stage['stage_result'] = rcd.approval_decision
                    break

        return approval_exists, approval_result, next_stage_lst
