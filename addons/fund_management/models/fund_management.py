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
            _logger.info(f"record={record}")

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
    meeting_minutes = fields.Html(string="Meeting Minutes", tracking=True)
    meeting_minutes_editable = fields.Boolean("Meeting Minutes Editable", related="stage.input_meeting_minutes")

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        default_category_id = self._get_default_category()

        _logger.info(f"进入_get_view default_category_id={default_category_id}")

        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form':
            stage_node = next(iter(arch.xpath('//field[@name="stage"]')), None)
            if stage_node is not None:
                stage_node.attrib['domain'] = f"[('company_id', '=', company_id), " \
                                              f"('category_id', '=', {default_category_id})]"

        return arch, view

    def _get_stage_domain(self):

        default_category_id = self._get_default_category()
        _logger.info(f"default_category_id={default_category_id}")
        _logger.info(f"active_id={self.env.context.get('active_id')}")
        stage_domain = [('company_id', '=', self.env.user.company_id.id), ('category_id', '=', default_category_id)]

        _logger.info(f"stage_domain={stage_domain}")
        self._get_view()
        return stage_domain

    stage = fields.Many2one('fund.management.approval.stage', ondelete='restrict', copy=False, tracking=True,
                            domain=lambda self: self._get_stage_domain(),
                            default=lambda self: self._get_default_stage_id())
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
        currency_field='currency_id',
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
        currency_field='currency_id',
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

        _logger.info(f"stage_ids={stage_ids}")
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

    def _compute_nb_attachment(self):
        attachment_data = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'fund.management'), ('res_id', 'in', self.ids)],
            ['res_id'],
            ['__count'],
        )
        attachment = dict(attachment_data)
        for expense in self:
            expense.nb_attachment = attachment.get(expense._origin.id, 0)
            _logger.info(f"id:{expense._origin.id};.nb_attachment={expense.nb_attachment}")

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
        _logger.info(f"self.env.context={self.env.context}")
        for record in self:
            stage_ids = self.env['fund.management.approval.stage']. \
                search([('company_id', '=', self.env.user.company_id.id),
                        ('category_id', '=', self.env.context.get('default_category_id'))], limit=1)

            if stage_ids:
                return stage_ids[0]
            else:
                return False

    def action_save_fund_management(self):
        for record in self:
            if record.state != 'draft':
                record.state = 'draft'
            default_stage = self._get_default_stage_id()
            if record.stage != default_stage:
                record.stage = default_stage

        return

    def action_submit_fund_management(self):
        self.action_agree()

    def action_agree(self):
        # 批准
        for record in self:
            if record.stage.sequence and (not self._check_approval_rights(record)):
                raise UserError(f"您不能审批当前阶段：{record.stage.name}")

            next_state = 'submitted' if record.stage.sequence == 0 else 'approved'
            # 先创建当前阶段的审批记录
            self._create_approval_detail(record, True, False)
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

    def action_reject(self):
        # 驳回
        for record in self:
            if not record.stage.sequence:
                return

            if record.stage.sequence and (not self._check_approval_rights(record)):
                raise UserError(f"您不能审批当前阶段：{record.stage.name}")

            # 先创建当前阶段的驳回记录
            self._create_approval_detail(record, False, False)

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

            if record.stage.sequence and (not self._check_approval_rights(record)):
                raise UserError(f"您不能操作当前阶段：{record.stage.name}")

            self._create_approval_detail(record, False, True)
            all_stages = self.env['fund.management.approval.stage'].search([('company_id', '=', record.company_id.id),
                                                                            (
                                                                            'category_id', '=', record.category_id.id)])
            for each_stage in all_stages:
                if each_stage.sequence == 1000:
                    record.stage = each_stage
                    self.write({'stage': record.stage})
                    return

    def _check_approval_rights(self, record):
        record_stage_dep_id = record.stage.op_department_id.id
        record_stage_job_id = record.stage.op_job_id.id

        this_employee_dep_id = self._get_employee().department_id.id
        this_employee_job_id = self._get_employee().job_id.id

        if not self.env.user.has_group('fund_management.group_fund_management_team_approver'):
            return False

        if this_employee_dep_id == record_stage_dep_id and record_stage_job_id == this_employee_job_id:
            return True
        else:
            return False

    def _create_approval_detail(self, record, approval_or_reject, is_cancel):

        _logger.info(f"datetime.now()[{datetime.now()}]")
        date_time = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        _logger.info(f"date:{date_time}")

        this_user = self._get_employee()
        approval_by_usr_id = this_user.id
        approval_by_usr_nm = this_user.name

        if approval_or_reject:
            approval_decision_txt = "同意"
            approval_comment = "同意"
        else:
            approval_decision_txt = "驳回"
            approval_comment = "驳回"

        if record.stage.sequence == 0:
            rcd_exists = self.env['fund.management.approval.detail'].browse(
                record.approval_detail_ids.ids).exists()

            if rcd_exists:
                approval_comment = "再提交"
            else:
                approval_comment = "新建"

        if is_cancel:
            approval_decision_txt = "取消"
            approval_comment = "取消"

        _logger.info(f"创建审批记录approval_or_reject={approval_or_reject}")
        self.env['fund.management.approval.detail'].create({
            'fund_management_id': f"{record.id}",
            'approval_stage': f"{record.stage.id}",
            'approval_stage_id': f"{record.stage.id}",
            'approval_stage_nm': f"{record.stage.name}",
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
            [('employee_id', 'in', self.env.user.employee_ids.ids),
             ('state', 'in', ('submitted', 'approved', 'done'))
             ], ['state'], ['total_amount:sum'])
        for state, total_amount_sum in expenses:
            # if state in {'draft'}:  # Fuse the two states into only one "To Submit" state
            #     state = 'to_submit'
            expense_state[state]['amount'] += total_amount_sum
        return expense_state

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
        _logger.info(f"self_rcd_id={self_rcd_id};default_category_id={default_category_id}")
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
        _logger.info(f"default_category_id={default_category_id}")
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

        # return self.env["ir.actions.act_window"]._for_xml_id('fund_management.view_all_stage_by_category_action')
