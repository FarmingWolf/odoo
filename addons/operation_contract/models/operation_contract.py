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

    page_editable = fields.Boolean("page_editable", readonly=True, store=False, compute="_compute_page_editable")
    op_person_id = fields.Many2one('hr.employee', string='经办人', default=lambda self: self._get_employee())
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)

    # 使用related属性将employee_id中的某些字段映射到custom.model中
    department_id = fields.Many2one('hr.department', related='op_person_id.department_id', string="部门")
    job_title = fields.Char(related='op_person_id.job_title', string="职务")
    op_person_phone = fields.Char(related='op_person_id.mobile_phone', string="电话")

    partner_id = fields.Many2one('res.partner', string='公司名称', tracking=True)
    partner_contact_id = fields.Char(string='联系人', compute='_compute_contact_info', readonly=True)
    partner_contact_id_no = fields.Char(string='联系人身份证号', compute='_compute_contact_info', readonly=True)
    partner_contact_phone = fields.Char(string='联系电话', compute='_compute_contact_info', readonly=True)
    partner_contact_mobile = fields.Char(string='联系手机', compute='_compute_contact_info', readonly=True)
    partner_contact_position = fields.Char(string='联系人职务', compute='_compute_contact_info', readonly=True)
    partner_charger_id = fields.Char(string='责任人', compute='_compute_contact_info', readonly=True)
    partner_charger_id_no = fields.Char(string='责任人身份证号', compute='_compute_contact_info', readonly=True)
    partner_charger_phone = fields.Char(string='责任电话', compute='_compute_contact_info', readonly=True)
    partner_charger_mobile = fields.Char(string='责任手机', compute='_compute_contact_info', readonly=True)
    partner_charger_position = fields.Char(string='责任人职务', compute='_compute_contact_info', readonly=True)

    comments = fields.Text(string="备注")

    date_approval_begin = fields.Date(copy=False, string="审批发起日期", readonly=True,
                                      default=lambda self: fields.Date.context_today(self))
    date_begin = fields.Datetime(copy=False, string="合同开始日期", tracking=True)
    date_end = fields.Datetime(copy=False, string="合同结束日期", tracking=True)
    contract_amount = fields.Float(string="合同金额（元）", copy=False, default=0.0, digits=(16, 2))
    description = fields.Html(string='合同详情', store=True, readonly=False)
    event_location_id = fields.Many2many('event.track.location', 'operation_contract_location_rel', 'contract_id',
                                         'location_id', string='活动地点', copy=False, tracking=True)
    event_tag_ids = fields.Many2many('event.tag', 'operation_contract_event_tag_rel', 'contract_id',
                                     'tag_id', string="活动类型", readonly=False, store=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string="附件", copy=False)

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
        _logger.info(f"param-crowd=[{param}],rs=[{rs}]")
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

    @api.model
    def _get_security_check_method_options(self):
        options = self._get_event_options('雇佣安检人员')
        _logger.info(f"_get_security_check_method_options=[{options}]")
        return options

    @api.model
    def _get_security_equipment_method_options(self):
        options = self._get_event_options('使用安检器材')
        _logger.info(f"_get_security_equipment_method_options=[{options}]")
        return options

    security_guard_method = fields.Selection(selection=_get_security_guard_method_options, string="雇佣安保人员",
                                             tracking=True, store=True)
    security_guard_company = fields.Many2one('res.partner', string='安保公司', tracking=True)
    security_guard_company_show = fields.Boolean(
        string='显示安保公司', compute=lambda self: self._compute_company_show('security_guard_method'))

    security_guard_charger_id = fields.Char(string='安保责任人', compute='_compute_guard_charger_info', readonly=True)
    security_guard_charger_phone = fields.Char(string='安保责任人电话', compute='_compute_guard_charger_info', readonly=True)
    security_guard_charger_mobile = fields.Char(string='安保责任人手机', compute='_compute_guard_charger_info', readonly=True)

    security_check_method = fields.Selection(selection=_get_security_check_method_options, string="雇佣安检人员",
                                             tracking=True, store=True)
    security_check_company = fields.Many2one('res.partner', string='安检公司', tracking=True)
    security_check_company_show = fields.Boolean(
        string='显示安检公司', compute=lambda self: self._compute_company_show('security_check_method'))

    security_check_charger_id = fields.Char(string='安检责任人', compute='_compute_check_charger_info', readonly=True)
    security_check_charger_phone = fields.Char(string='安检责任人电话', compute='_compute_check_charger_info', readonly=True)
    security_check_charger_mobile = fields.Char(string='安检责任人手机', compute='_compute_check_charger_info', readonly=True)

    security_equipment_method = fields.Selection(selection=_get_security_equipment_method_options, string="使用安检器材",
                                                 tracking=True, store=True)
    security_equipment_company = fields.Many2one('res.partner', string='安检器材公司', tracking=True)
    security_equipment_comment = fields.Text(string="安检设备种类及数量", tracking=True)
    security_equipment_company_show = fields.Boolean(
        string='显示安检器材公司', compute=lambda self: self._compute_company_show('security_equipment_method'))

    security_equipment_charger_id = fields.Char(string='器材公司责任人', readonly=True,
                                                compute='_compute_equipment_charger_info')
    security_equipment_charger_phone = fields.Char(string='电话', readonly=True,
                                                   compute='_compute_equipment_charger_info')
    security_equipment_charger_mobile = fields.Char(string='手机', readonly=True,
                                                    compute='_compute_equipment_charger_info')

    @api.depends('stage_id')
    def _compute_page_editable(self):
        self.ensure_one()
        res = False
        for record in self:
            if "运营" in record.stage_id.op_department_id.name:
                if self.env.user.has_group('operation_contract.operation_dep_contract_operator'):
                    res = True
            record.page_editable = res
        return res

    @api.depends('security_guard_company')
    def _compute_guard_charger_info(self):
        for record in self:
            # 查找partner的child_ids中is_company=False的记录，这通常代表个人联系人
            contact = record.security_guard_company.child_ids.filtered(lambda r: not r.is_company)
            if contact:
                for each_c in contact:
                    check_str = str(each_c.name) + str(each_c.title.name) + str(each_c.function) + str(each_c.comment)
                    _logger.info(f"check_str=[{check_str}]")
                    if '责' in check_str:
                        record.security_guard_charger_id = each_c.name
                        record.security_guard_charger_phone = each_c.phone
                        record.security_guard_charger_mobile = each_c.mobile

                if not record.security_guard_charger_id:
                    record.security_guard_charger_id = contact[0].name
                    record.security_guard_charger_phone = contact[0].phone
                    record.security_guard_charger_mobile = contact[0].mobile

            else:
                record.security_guard_charger_id = False
                record.security_guard_charger_phone = False
                record.security_guard_charger_mobile = False

    @api.depends('security_check_company')
    def _compute_check_charger_info(self):
        for record in self:
            # 查找partner的child_ids中is_company=False的记录，这通常代表个人联系人
            contact = record.security_check_company.child_ids.filtered(lambda r: not r.is_company)
            if contact:
                for each_c in contact:
                    check_str = str(each_c.name) + str(each_c.title.name) + str(each_c.function) + str(each_c.comment)
                    _logger.info(f"check_str=[{check_str}]")
                    if '责' in check_str:
                        record.security_check_charger_id = each_c.name
                        record.security_check_charger_phone = each_c.phone
                        record.security_check_charger_mobile = each_c.mobile

                if not record.security_check_charger_id:
                    record.security_check_charger_id = contact[0].name
                    record.security_check_charger_phone = contact[0].phone
                    record.security_check_charger_mobile = contact[0].mobile

            else:
                record.security_check_charger_id = False
                record.security_check_charger_phone = False
                record.security_check_charger_mobile = False

    @api.depends('security_equipment_company')
    def _compute_equipment_charger_info(self):
        for record in self:
            # 查找partner的child_ids中is_company=False的记录，这通常代表个人联系人
            contact = record.security_equipment_company.child_ids.filtered(lambda r: not r.is_company)
            if contact:
                for each_c in contact:
                    check_str = str(each_c.name) + str(each_c.title.name) + str(each_c.function) + str(each_c.comment)
                    _logger.info(f"check_str=[{check_str}]")
                    if '责' in check_str:
                        record.security_equipment_charger_id = each_c.name
                        record.security_equipment_charger_phone = each_c.phone
                        record.security_equipment_charger_mobile = each_c.mobile

                if not record.security_equipment_charger_id:
                    record.security_equipment_charger_id = contact[0].name
                    record.security_equipment_charger_phone = contact[0].phone
                    record.security_equipment_charger_mobile = contact[0].mobile

            else:
                record.security_equipment_charger_id = False
                record.security_equipment_charger_phone = False
                record.security_equipment_charger_mobile = False

    @api.depends('security_guard_method', 'security_check_method', 'security_equipment_method')
    def _compute_company_show(self, check_tgt):
        for record in self:
            # _logger.info(f"check_tgt={check_tgt},tgt_str={tgt_str}")
            _logger.info(f"record.security_guard_method=【{record.security_guard_method}】")
            _logger.info(f"record.security_check_method=【{record.security_check_method}】")
            _logger.info(f"record.security_equipment_method=【{record.security_equipment_method}】")
            # _logger.info(f"record._fields[check_tgt]={record._fields[check_tgt]}")  # 这是字段
            # _logger.info(f"record._fields[check_tgt].selection={record._fields[check_tgt].selection}")  # 是函数，不能用
            # _logger.info(f"r_description_string={record._fields[check_tgt]._description_string(self.env)}")  # 这个有用
            # _logger.info(f"get_description={record._fields[check_tgt].get_description(self.env)}")  # 这里有selection集合

            # _logger.info(f"dict_guard_selection={dict(record._fields['security_guard_method'].get_description(self.env)).get('selection')}")
            # _logger.info(f"dict_check_selection={dict(record._fields['security_check_method'].get_description(self.env)).get('selection')}")
            # _logger.info(f"dict_equipment_selection={dict(record._fields['security_equipment_method'].get_description(self.env)).get('selection')}")
            #
            # record.security_guard_method = int(record.security_guard_method)
            # record.security_check_method = int(record.security_check_method)
            # record.security_equipment_method = int(record.security_equipment_method)
            #
            # _logger.info(f"→→→.security_guard_method={record.security_guard_method}")
            # _logger.info(f"→→→.security_check_method={record.security_check_method}")
            # _logger.info(f"→→→.security_equipment_method={record.security_equipment_method}")

            tgt_selection = dict(record._fields[check_tgt].get_description(self.env)).get('selection')
            # _logger.info(f"tgt_selection={tgt_selection}")
            dict_selection = dict(tgt_selection)
            _logger.info(f"检查对象的dict_selection={dict_selection}")
            dict_dict_selection = dict(dict_selection)
            _logger.info(f"检查对象的dict(dict_selection)={dict_dict_selection}")

            show = False
            if check_tgt == "security_guard_method":
                if record.security_guard_method:
                    option_selected = dict_dict_selection.get(int(record.security_guard_method))
                    record.security_guard_method = int(record.security_guard_method)
                    _logger.info(f"security_check_method的option_selected={option_selected}")
                    show = '另行' in option_selected
                else:
                    show = False
                record.security_guard_company_show = show
                _logger.info(f"→→→.security_guard_company_show={record.security_guard_company_show}")

            elif check_tgt == "security_check_method":
                if record.security_check_method:
                    option_selected = dict_dict_selection.get(int(record.security_check_method))
                    record.security_check_method = int(record.security_check_method)
                    _logger.info(f"security_check_method的option_selected={option_selected}")
                    show = '另行' in option_selected
                else:
                    show = False
                record.security_check_company_show = show
                _logger.info(f"→→→.security_check_company_show={record.security_check_company_show}")

            elif check_tgt == "security_equipment_method":
                if record.security_equipment_method:
                    option_selected = dict_dict_selection.get(int(record.security_equipment_method))
                    record.security_equipment_method = int(record.security_equipment_method)
                    _logger.info(f"security_equipment_method的option_selected={option_selected}")
                    show = '另行' in option_selected
                else:
                    show = False
                record.security_equipment_company_show = show
                _logger.info(f"→→→.security_equipment_company_show={record.security_equipment_company_show}")
            else:
                _logger.error(f"与未知check_tgt不期而遇：【{check_tgt}】")

            return show

    @api.onchange('security_guard_method')
    def _on_security_guard_method_change(self):
        for record in self:
            self._compute_company_show('security_guard_method')

    @api.onchange('security_check_method')
    def _on_security_check_method_change(self):
        for record in self:
            self._compute_company_show('security_check_method')

    @api.onchange('security_equipment_method')
    def _on_security_equipment_method_change(self):
        for record in self:
            self._compute_company_show('security_equipment_method')

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
        _logger.info(f"貌似只有新建记录时才会default_get方法fields_list={fields_list}")
        default_result = super().default_get(fields_list)
        _compute_date_begin_end(fields_list, default_result)

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

        _logger.info(f"当前{self.env.user}在更新")
        _logger.info(f"更新内容有：{vals}")

        if not vals.get('security_guard_method'):
            for record in self:
                vals['security_guard_method'] = int(record.security_guard_method)
                track_messages = record.message_ids.filtered(
                    lambda m: m.subtype_id == self.env.ref('mail.mt_note') and 'security_guard_method' in m.body)
                track_messages.write({'needaction_partner_ids': [(6, 0, [])]})

        if not vals.get('security_check_method'):
            for record in self:
                vals['security_check_method'] = int(record.security_check_method)
                track_messages = record.message_ids.filtered(
                    lambda m: m.subtype_id == self.env.ref('mail.mt_note') and 'security_check_method' in m.body)
                track_messages.write({'needaction_partner_ids': [(6, 0, [])]})

        if not vals.get('security_equipment_method'):
            for record in self:
                vals['security_equipment_method'] = int(record.security_equipment_method)
                track_messages = record.message_ids.filtered(
                    lambda m: m.subtype_id == self.env.ref('mail.mt_note') and 'security_equipment_method' in m.body)
                track_messages.write({'needaction_partner_ids': [(6, 0, [])]})

        res = super(OperationContract, self).write(vals)
        return res

    def unlink(self):
        res = super(OperationContract, self).unlink()
        return res

    # def _message_post_after_hook(self, message, msg_vals):
    #     # 获取当前记录的实例
    #     record = self.browse(msg_vals['res_id'])
    #     _logger.info(f"self message={self.message}")
    #     _logger.info(f"param message={message}")
    #     _logger.info(f"param msg_vals={msg_vals}")
    #     _logger.info(f"message.subtype_id={message.subtype_id}self.env('mail.mt_note')={self.env.ref('mail.mt_note')}")
    #     _logger.info(f"message.body={message.body}")
    #     _logger.info(f"record.message_partner_ids={record.message_partner_ids}")
    #     # 如果消息类型是内部笔记 (mail.mt_note) 并且消息内容包含 field_a 的变更记录
    #     if message.subtype_id == self.env.ref('mail.mt_note') and \
    #             ('contract_amount' in message.body or 'attachment_ids' in message.body):
    #         # 获取所有订阅者
    #         partners = record.message_partner_ids
    #         # 筛选出没有查看权限的用户
    #         excluded_partners = partners.filtered(
    #             lambda p: p.user_ids.has_group('operation_contract.estate_management_dep_contract_read'))
    #         # 获取允许查看的伙伴 ID
    #         allowed_partners = partners - excluded_partners
    #         # 更新消息的订阅者
    #         message.write({'partner_ids': [(6, 0, allowed_partners.ids)]})
    #         _logger.info(f"message.partner_ids={message.partner_ids}")
    #     # 调用父类的方法
    #     return super(OperationContract, self)._message_post_after_hook(message, msg_vals)

    # @api.onchange('security_guard_method', 'security_check_method', 'security_equipment_method')
    # def _onchange_selection_fields(self):
    #     # 非编辑阶段，不记录这三个字段的变更
    #     for record in self:
    #         if record.stage_sequence > 10:
    #             self._origin._message_untrack(['security_guard_method'])
    #             self._origin._message_untrack(['security_check_method'])
    #             self._origin._message_untrack(['security_equipment_method'])

    # def _message_log(self, body, subject=None, message_type='notification', **kwargs):
    #     self.ensure_one()
    #     contract_amount_field_id = self.env['ir.model.fields']._get('operation.contract.contract', 'contract_amount').id
    #     attachment_filed_id = self.env['ir.model.fields']._get('operation.contract.contract', 'attachment_ids').id
    #     security_guard_method_field_id = self.env['ir.model.fields']._get('operation.contract.contract',
    #                                                                       'security_guard_method').id
    #     security_check_method_field_id = self.env['ir.model.fields']._get('operation.contract.contract',
    #                                                                       'security_check_method').id
    #     security_equipment_method_field_id = self.env['ir.model.fields']._get('operation.contract.contract',
    #                                                                           'security_equipment_method').id
    #     _logger.info(
    #         f"contract_amount_field_id={contract_amount_field_id},attachment_filed_id={attachment_filed_id},"
    #         f"security_guard_method_field_id={security_guard_method_field_id}，"
    #         f"security_check_method_field_id={security_check_method_field_id}，"
    #         f"security_equipment_method_field_id={security_equipment_method_field_id}")
    #
    #     for record in self:
    #         new_tracked_fields = []
    #         # 当前非编辑stage时，就不应该有上述几个字段的track
    #         if record.stage_sequence > 10:
    #             for tracked_value_id in kwargs['tracking_value_ids']:
    #                 if tracked_value_id[2]['field_id'] in (
    #                         security_guard_method_field_id, security_check_method_field_id,
    #                         security_equipment_method_field_id):
    #                     pass
    #                     # # 获取所有订阅者
    #                     # partners = record.message_partner_ids
    #                     # _logger.info(f"当前partners={partners}")
    #                     # # 筛选出没有查看权限的用户
    #                     # excluded_partners = partners.filtered(
    #                     #     lambda p: p.user_ids.has_group('operation_contract.estate_management_dep_contract_read'))
    #                     # _logger.info(f"excluded_partners={excluded_partners}")
    #                     # # 获取允许查看的伙伴 ID
    #                     # allowed_partners = partners - excluded_partners
    #                     # _logger.info(f"allowed_partners={allowed_partners}")
    #                     # # 更新消息的订阅者
    #                     # kwargs['partner_ids'] = allowed_partners.ids
    #                 else:
    #                     new_tracked_fields.append(tracked_value_id)
    #
    #             kwargs['tracking_value_ids'] = new_tracked_fields
    #
    #     _logger.info(f"kwargs={kwargs}")
    #     return super()._message_log(subject=subject, message_type=message_type, **kwargs)
