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


def _check_rights(self, record):
    record_stage_dep_id = record.stage_id.op_department_id.id
    _logger.info(f"record.stage_id.op_department_id.id={record_stage_dep_id}")
    this_employee_dep_id = self._get_employee_dp()
    _logger.info(f"this.user.employee.department_id={this_employee_dep_id.id}")

    return this_employee_dep_id.id == record_stage_dep_id or self.env.user.id <= 2


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ['res.partner']

    person_id_no = fields.Char(string="身份证号")

    @api.model
    def default_get(self, fields_list):
        default_result = super().default_get(fields_list)

        """_logger.info(f"进入时fields_list={fields_list}")
        _logger.info(f"进入时default_result={default_result}")
        _logger.info(f"进入时context={self.env.context}")
        #if 'type' in fields_list:
            # if default_result.get('type') == 'other':
            #     default_result['type'] = 'contact'
        """
        return default_result


def _compute_security_guard_method(field_str, fields_list, default_result):
    _logger.info(f'_compute_security_guard_method:field_str=【{field_str}】')
    _logger.info(f'_compute_security_guard_method:fields_list=【{fields_list}】')
    _logger.info(f'_compute_security_guard_method:default_result=【{default_result}】')
    if field_str in fields_list and field_str not in default_result:
        default_result[field_str] = dict(fields_list).get(field_str)


def _compute_date_begin_end(fields_list, default_result):

    if 'date_begin' in fields_list and 'date_begin' not in default_result:
        now = fields.Datetime.now()
        # Round the datetime to the nearest half hour (e.g. 08:17 => 08:30 and 08:37 => 09:00)
        default_result['date_begin'] = now.replace(second=0, microsecond=0) + timedelta(minutes=-now.minute % 30)
    if 'date_end' in fields_list and 'date_end' not in default_result and default_result.get('date_begin'):
        default_result['date_end'] = default_result['date_begin'] + timedelta(days=1)

    return default_result


class OperationContract(models.Model):
    _name = "operation.contract.contract"
    _description = "运营合同模型"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_begin, id'

    name = fields.Char('合同名称', required=True, translate=True, tracking=True)
    contract_no = fields.Char(string='合同编号', readonly=True, default=lambda self: self._get_contract_no(False),
                              store=True)

    op_person_id = fields.Many2one('hr.employee', string='经办人', default=lambda self: self._get_employee())
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)

    # 使用related属性将employee_id中的某些字段映射到custom.model中
    department_id = fields.Many2one('hr.department', related='op_person_id.department_id', string="部门")
    job_title = fields.Char(related='op_person_id.job_title', string="职务")

    partner_id = fields.Many2one('res.partner', string='公司名称', tracking=True)
    partner_contact_id = fields.Char(string='联系人', compute='_compute_contact_info', readonly=True)
    partner_contact_id_no = fields.Char(string='身份证号', compute='_compute_contact_info', readonly=True)
    partner_contact_phone = fields.Char(string='联系电话', compute='_compute_contact_info', readonly=True)
    partner_contact_mobile = fields.Char(string='联系手机', compute='_compute_contact_info', readonly=True)
    partner_contact_position = fields.Char(string='职务', compute='_compute_contact_info', readonly=True)
    partner_charger_id = fields.Char(string='责任人', compute='_compute_contact_info', readonly=True)
    partner_charger_id_no = fields.Char(string='身份证号', compute='_compute_contact_info', readonly=True)
    partner_charger_phone = fields.Char(string='责任电话', compute='_compute_contact_info', readonly=True)
    partner_charger_mobile = fields.Char(string='责任手机', compute='_compute_contact_info', readonly=True)
    partner_charger_position = fields.Char(string='职务', compute='_compute_contact_info', readonly=True)

    comments = fields.Text(string="备注")

    date_approval_begin = fields.Date(copy=False, string="审批发起日期", readonly=True,
                                      default=lambda self: fields.Date.context_today(self))
    date_begin = fields.Datetime(copy=False, string="合同开始日期", tracking=True)
    date_end = fields.Datetime(copy=False, string="合同结束日期", tracking=True)
    contract_amount = fields.Float(string="合同金额（元）", copy=False, default=0.0, digits=(16, 2))
    description = fields.Html(string='合同详情', store=True, readonly=False, tracking=True)
    event_location_id = fields.Many2many('event.track.location', 'operation_contract_location_rel', 'contract_id',
                                         'location_id', string='Event Location', copy=False)
    event_tag_ids = fields.Many2many('event.tag', 'operation_contract_event_tag_rel', 'contract_id',
                                     'tag_id', string="活动类型", readonly=False, store=True)

    def _get_default_stage_id(self):
        return self.env['operation.contract.stage'].search([], limit=1)

    stage_id = fields.Many2one(
        'operation.contract.stage', ondelete='restrict', default=_get_default_stage_id,
        group_expand='_read_group_stage_ids', copy=False, tracking=True)
    stage_sequence = fields.Integer(string="状态序号", related="stage_id.sequence")
    stage_op_department_id = fields.Many2one(string="状态审批部门", related="stage_id.op_department_id")
    # Kanban fields
    kanban_state = fields.Selection([('normal', '推进中'), ('done', '已完成'), ('blocked', '任务受阻')], default='normal',
                                    copy=False, tracking=True)
    kanban_state_label = fields.Char(
        string='看板状态', compute='_compute_kanban_state_label',
        store=True)

    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='任务受阻解释说明', readonly=True)
    legend_done = fields.Char(related='stage_id.legend_done', string='任务已完成说明', readonly=True)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='任务推进中说明', readonly=True)

    approval_detail_ids = fields.One2many('operation.contract.approval.detail', 'contract_id', string="审批情况")

    @api.model
    def _get_event_options(self, param):
        rs = self.env['event.option'].search(
            [('group_id', 'in', self.env['event.option.group'].search(
                [('name', '=', param)]).mapped('id'))])
        _logger.info(f"param=[{param}],rs=[{rs}]")
        option_created = [(r.id, r.name) for r in rs]
        _logger.info(f"option_created=[{option_created}]")
        return option_created

    @api.model
    def _get_event_options_crowd(self, param):
        rs = self.env['event.option'].search(
            [('group_id', 'in', self.env['event.option.group'].search(
                [('name', '=', param)]).mapped('id'))])
        _logger.info(f"param=[{param}],rs=[{rs}]")
        return rs.ids

    @api.model
    def _get_crowd_control_method_option_domain(self):
        options = self._get_event_options_crowd('控制人数措施')
        _logger.info(f"_get_crowd_control_method_option_domain=[{options}]")

        domain = [('id', 'in', options)]
        return domain

    seats_max = fields.Integer(string='最多参与人数', readonly=False, store=True, tracking=True)
    seats_limited = fields.Boolean(string='限制参与人数', store=True)
    crowd_control_method = fields.Many2many('event.option', 'operation_contract_crowd_control_method', 'contract_id',
                                            'option_id', string="控制人数措施", tracking=True, readonly=False,
                                            domain=_get_crowd_control_method_option_domain)

    def _get_security_guard_method_options(self):
        options = self._get_event_options('雇佣安保人员')
        _logger.info(f"_get_security_guard_method_options=[{options}]")
        return options

    def _get_security_check_method_options(self):
        options = self._get_event_options('雇佣安检人员')
        _logger.info(f"_get_security_check_method_options=[{options}]")
        return options

    def _get_security_equipment_method_options(self):
        options = self._get_event_options('使用安检器材')
        _logger.info(f"_get_security_equipment_method_options=[{options}]")
        return options

    security_guard_method = fields.Selection(selection=_get_security_guard_method_options, string="雇佣安保人员",
                                             tracking=True, store=True)
    security_guard_company = fields.Many2one('res.partner', string='安保公司', tracking=True)
    security_guard_company_show = fields.Boolean(
        string='显示安保公司', precompute=True, store=True,
        compute=lambda self: self._compute_check_show('security_guard_method', '雇佣安保人员'))

    security_check_method = fields.Selection(selection=_get_security_check_method_options, string="雇佣安检人员",
                                             tracking=True, store=True)
    security_check_company = fields.Many2one('res.partner', string='安检公司', tracking=True)
    security_check_company_show = fields.Boolean(
        string='显示安检公司', precompute=True, store=True,
        compute=lambda self: self._compute_check_show('security_check_method', '雇佣安检人员'))

    security_equipment_method = fields.Selection(selection=_get_security_equipment_method_options, string="使用安检器材",
                                                 tracking=True, store=True)
    security_equipment_company = fields.Many2one('res.partner', string='安检器材公司', tracking=True)
    security_equipment_comment = fields.Char(string="安检设备种类及数量", tracking=True)
    security_equipment_company_show = fields.Boolean(
        string='显示安检器材公司', precompute=True, store=True,
        compute=lambda self: self._compute_check_show('security_equipment_method', '使用安检器材'))

    @api.depends('security_guard_method', 'security_check_method', 'security_equipment_method')
    def _compute_check_show(self, check_tgt, tgt_str):
        for record in self:
            # options = self._get_event_options(tgt_str)

            _logger.info(f"check_tgt={check_tgt},tgt_str={tgt_str}")
            # _logger.info(f"options={options}")
            _logger.info(f"record._fields[check_tgt]={record._fields[check_tgt]}")  # 这是字段
            _logger.info(f"record._fields[check_tgt].selection={record._fields[check_tgt].selection}")  # 是函数，不能用
            _logger.info(f"r_description_string={record._fields[check_tgt]._description_string(self.env)}")  # 这个有用
            _logger.info(f"get_description={record._fields[check_tgt].get_description(self.env)}")  # 这里有selection集合

            tgt_selection = dict(record._fields[check_tgt].get_description(self.env)).get('selection')
            _logger.info(f"tgt_selection={tgt_selection}")
            dict_selection = dict(tgt_selection)
            _logger.info(f"dict_selection={dict_selection}")

            if check_tgt == "security_guard_method":
                if record.security_guard_method:
                    show = '另行' in dict(dict_selection).get(record.security_guard_method)
                else:
                    show = False
                record.security_guard_company_show = show
            elif check_tgt == "security_check_method":
                if record.security_check_method:
                    show = '另行' in dict(dict_selection).get(record.security_check_method)
                else:
                    show = False
                record.security_check_company_show = show
            elif check_tgt == "security_equipment_method":
                if record.security_equipment_method:
                    show = '另行' in dict(dict_selection).get(record.security_equipment_method)
                else:
                    show = False
                record.security_equipment_company_show = show

            return show

    @api.onchange('security_guard_method')
    def _on_security_guard_method_change(self):
        for record in self:
            _logger.info(f"_on_security_guard_method_change={record.security_guard_method}")
            self._compute_check_show('security_guard_method', '雇佣安保人员')

    @api.onchange('security_check_method')
    def _on_security_check_method_change(self):
        for record in self:
            _logger.info(f"_on_security_check_method_change={record.security_check_method}")
            self._compute_check_show('security_check_method', '雇佣安检人员')

    @api.onchange('security_equipment_method')
    def _on_security_equipment_method_change(self):
        for record in self:
            _logger.info(f"_on_security_equipment_method={record.security_equipment_method}")
            self._compute_check_show('security_equipment_method', '使用安检器材')

    @api.depends('partner_id')
    def _compute_contact_info(self):
        for record in self:
            # 查找partner的child_ids中is_company=False的记录，这通常代表个人联系人
            contact = record.partner_id.child_ids.filtered(lambda r: not r.is_company)
            if contact:
                for each_c in contact:
                    check_str = str(each_c.name) + str(each_c.title.name) + str(each_c.function) + str(each_c.comment)
                    _logger.info(f"check_str=[{check_str}]")
                    if '联' in check_str:
                        record.partner_contact_id = each_c.name
                        record.partner_contact_id_no = each_c.person_id_no
                        record.partner_contact_phone = each_c.phone
                        record.partner_contact_mobile = each_c.mobile
                        record.partner_contact_position = each_c.function
                    elif '责' in check_str:
                        record.partner_charger_id = each_c.name
                        record.partner_charger_id_no = each_c.person_id_no
                        record.partner_charger_phone = each_c.phone
                        record.partner_charger_mobile = each_c.mobile
                        record.partner_charger_position = each_c.function

                if not record.partner_contact_id:
                    record.partner_contact_id = contact[0].name
                    record.partner_contact_id_no = contact[0].person_id_no
                    record.partner_contact_phone = contact[0].phone
                    record.partner_contact_mobile = contact[0].mobile
                    record.partner_contact_position = contact[0].function
                if not record.partner_charger_id:
                    record.partner_charger_id = contact[0].name
                    record.partner_charger_id_no = contact[0].person_id_no
                    record.partner_charger_phone = contact[0].phone
                    record.partner_charger_mobile = contact[0].mobile
                    record.partner_charger_position = contact[0].function

            else:
                record.partner_contact_id = False
                record.partner_contact_id_no = False
                record.partner_contact_phone = False
                record.partner_contact_mobile = False
                record.partner_contact_position = False
                record.partner_charger_id = False
                record.partner_charger_id_no = False
                record.partner_charger_phone = False
                record.partner_charger_mobile = False
                record.partner_charger_position = False

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

    @api.depends('contract_no')
    def _compute_approval_details(self):
        for record in self:
            approval_details = self.env['operation.contract.approval.detail'].search(
                [('contract_id', '=', record.id)])
            for detail in approval_details:
                _logger.info(f"detail.approval_decision={detail.approval_decision}")
                _logger.info(f"detail.approval_by_id={detail.approved_by_id}")
                if detail.approval_decision:
                    detail.approval_decision_txt = "同意"
                elif detail.approval_date_time:  # 有操作时间
                    detail.approval_decision_txt = "驳回"
                else:
                    detail.approval_decision_txt = ""

            record.approval_detail_ids = approval_details

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
    def default_get(self, fields_list):
        """貌似只有新建记录时才会default_get方法"""
        default_result = super().default_get(fields_list)

        _compute_date_begin_end(fields_list, default_result)
        # _compute_security_guard_method('security_guard_method', fields_list, default_result)

        return default_result

    @api.model
    def ondelete(self):
        for record in self:
            if record.stage_id.sequence != 0 and record.stage_id.sequence != 1000:  # 0：新建；1000：canceled
                raise UserError(_('[{0}]该条合同状态为【{1}】，不可被删除!'.format(record.name, record.stage_id)))

        return super().unlink()

    def action_agree(self):
        # 批准
        for record in self:
            if not _check_rights(self, record):
                raise UserError("当前数据状态超出您的审批权限！")

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
            if not _check_rights(self, record):
                raise UserError("当前数据状态超出您的审批权限！")

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
            if not _check_rights(self, record):
                raise UserError("当前数据状态超出您的操作权限！")

            _create_approval_detail(self, record, False, True)
            all_stages = self.env['operation.contract.stage'].search([])
            for each_stage in all_stages:
                if each_stage.sequence == 1000:
                    record.stage_id = each_stage
                    record.stage_sequence = each_stage.sequence
                    self.write({'stage_id': record.stage_id, 'stage_sequence': record.stage_sequence})
                    return

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

    @api.model
    def _get_employee_dp(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            return user.employee_ids[0].department_id  # 返回第一个employee记录ID
        else:
            return False  # 如果没有employee记录，则返回False

    @api.model
    def create(self, vals):
        if (not vals.get('contract_no')) or vals.get('contract_no') == "保存时将自动获取合同号":
            vals['contract_no'] = self._get_contract_no(True)

        res = super(OperationContract, self).create(vals)

        return res

    def write(self, vals):
        if 'crowd_control_method' in vals:
            for record in self:
                # record.crowd_control_method = [(6, 0, vals['crowd_control_method'])]
                _logger.info(f"record.crowd_control_method={record.crowd_control_method}")
                _logger.info(f"vals['crowd_control_method']={vals['crowd_control_method']}")

        res = super(OperationContract, self).write(vals)
        return res

    def unlink(self):
        res = super(OperationContract, self).unlink()
        return res
