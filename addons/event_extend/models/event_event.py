# -*- coding: utf-8 -*-
import logging
from datetime import timedelta, datetime

from odoo import api, models, SUPERUSER_ID, fields
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class EventEvent(models.Model):
    _inherit = 'event.event'

    event_map = fields.Image(string='活动地图', max_width=1024, max_height=1024)
    event_location_id = fields.Many2many('event.track.location', 'even_location_rel', 'event_id', 'location_id',
                                         string='Event Location', copy=False, tracking=True, store=True,
                                         compute="_compute_contract_info", precompute=True, readonly=False)
    event_event_venues = fields.One2many('event.event.venues', 'event_event_id', string="活动地点",
                                         tracking=True, required=True, precompute=True, readonly=False, store=True,
                                         compute="_compute_contract_info")
    stage_id_sequence = fields.Integer(store=False, related='stage_id.sequence', string='stage_id_sequence')
    reference_contract_id = fields.Many2one(
        'operation.contract.contract', string='运营合同', ondelete='restrict',
        domain="[('stage_id.sequence', '>=', 50), ('stage_id.sequence', '<=', 100)]", tracking=True)
    event_company_id = fields.Many2one('res.partner', string='公司名称', tracking=True, compute='_compute_company_info',
                                       readonly=False, store=True,
                                       domain="[('company_id', '=', company_id)]")
    event_company_charger_id = fields.Char(string='负责人', compute='_compute_company_info', readonly=False,
                                           tracking=True, store=True)
    event_company_charger_phone = fields.Char(string='联系电话', compute='_compute_company_info', readonly=False,
                                              tracking=True, store=True)
    event_company_charger_mobile = fields.Char(string='联系手机', compute='_compute_company_info', readonly=False,
                                               tracking=True, store=True)

    contract_visible = fields.Boolean('引用合同', default=True, tracking=True)
    need_electricity_info = fields.Char(string="需用电及功率", tracking=True)
    need_management_dept_assist_info = fields.Text(string="物业部门配合的内容及时间", tracking=True)
    operation_dep_opinion = fields.Text(string="运营部意见", tracking=True)
    op_person_id = fields.Many2one('hr.employee', string='现场负责人', default=lambda self: self._get_employee(),
                                   readonly=False, store=True, compute="_compute_contract_info",
                                   tracking=True, precompute=True,
                                   domain="[('company_id', '=', company_id)]")
    op_person_mobile = fields.Char(related='op_person_id.mobile_phone', string="电话", readonly=False, store=True,
                                   compute="_compute_contract_info", tracking=True, precompute=True)

    page_editable = fields.Boolean("page_editable", readonly=True, store=False, compute="_compute_page_editable")

    # 来自event.event的fields↓↓↓
    name = fields.Char(string='Event', translate=True, required=True, tracking=True, precompute=True, store=True,
                       compute="_compute_contract_info", readonly=False)
    date_begin = fields.Datetime(string='Start Date', required=True, tracking=True, precompute=True, store=True,
                                 compute="_compute_contract_info", readonly=False)
    date_end = fields.Datetime(string='End Date', required=True, tracking=True, precompute=True, store=True,
                               compute="_compute_contract_info", readonly=False)
    date_editable = fields.Boolean("date_editable", readonly=True, store=False, compute="_compute_date_editable")
    tag_ids = fields.Many2many('event.tag', string="Tags", tracking=True, precompute=True, store=True,
                               compute="_compute_contract_info")
    seats_max = fields.Integer(string='Maximum Attendees', readonly=False, store=True, tracking=True,
                               precompute=True, compute="_compute_contract_info")
    seats_limited = fields.Boolean('Limit Attendees', required=True, precompute=True, readonly=False, store=True,
                                   tracking=True, compute="_compute_contract_info")
    user_id = fields.Many2one('res.users', string='Responsible', tracking=True, store=True,
                              default=lambda self: self.env.user,
                              domain="[('company_id', '=', company_id)]")
    note = fields.Html(string='活动内容', store=True, compute="_compute_contract_info", precompute=True, readonly=False)

    def _ir_attachment_domain(self):
        # 只有新建阶段，有可能打开”添加行“附件列表，这时只看自己的
        for record in self:
            domain = [('company_id', '=', self.env.user.company_id.id), ('create_uid', '=', self.env.user.id)]
            if not record.stage_id_sequence or record.stage_id_sequence == 0:
                _logger.info(f"event_attachment_ids_domain={domain}")
                return domain

        # 其他阶段，在form的附件列表中，不用添加create_uid作为约束条件
        domain = [('company_id', '=', self.env.user.company_id.id)]
        _logger.info(f"event_attachment_ids_domain={domain}")
        return domain

    event_attachment_ids = fields.Many2many('ir.attachment', string="附件", copy=False, tracking=True,
                                            domain=_ir_attachment_domain)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends('reference_contract_id', 'event_company_id')
    def _compute_company_info(self):
        for record in self:
            if not record.reference_contract_id.partner_charger_id:
                # 查找partner的child_ids中is_company=False的记录，这通常代表个人联系人
                contact = record.event_company_id.child_ids.filtered(lambda r: not r.is_company)
                if contact:
                    for each_c in contact:
                        check_str = str(each_c.name) + str(each_c.title.name) + str(each_c.function) + str(
                            each_c.comment)
                        _logger.info(f"check_str=[{check_str}]")
                        if '责' in check_str:
                            record.event_company_charger_id = each_c.name
                            record.event_company_charger_phone = each_c.phone
                            record.event_company_charger_mobile = each_c.mobile
                        elif '联' in check_str:
                            record.event_company_charger_id = each_c.name
                            record.event_company_charger_phone = each_c.phone
                            record.event_company_charger_mobile = each_c.mobile

                    if not record.event_company_charger_id:
                        record.event_company_charger_id = contact[0].name
                        record.event_company_charger_phone = contact[0].phone
                        record.event_company_charger_mobile = contact[0].mobile

                else:
                    record.event_company_charger_id = False
                    record.event_company_charger_phone = False
                    record.event_company_charger_mobile = False
            else:
                record.event_company_charger_id = record.reference_contract_id.partner_charger_id
                record.event_company_charger_phone = record.reference_contract_id.partner_charger_phone
                record.event_company_charger_mobile = record.reference_contract_id.partner_charger_mobile

    @api.depends("stage_id", "contract_visible")
    def _compute_date_editable(self):
        for record in self:
            if record.contract_visible:
                record.date_editable = False
                return False
            else:
                record.date_editable = self._compute_page_editable()
                return record.date_editable

    @api.depends('stage_id', 'user_id')
    def _compute_page_editable(self):
        self.ensure_one()
        res = False

        if "运营" or '信息' in self.env.user.employee_ids[0].department_id.name:
            if self.env.user.has_group('operation_contract.operation_dep_contract_operator'):
                res = True

        for record in self:
            record.page_editable = res
        _logger.info(f"_compute_page_editable res={res}")
        return res

    # 来自event.event的fields↑↑↑

    @api.depends('reference_contract_id')
    def _compute_contract_info(self):
        for record in self:
            record.event_registrations_open = True
            if record.contract_visible and record.reference_contract_id:
                record.name = record.reference_contract_id.name
                record.event_location_id = record.reference_contract_id.event_location_id
                # 先删除再新增
                record.event_event_venues = False
                record.event_event_venues = self._set_event_venues_from_contract_venues(
                    record.reference_contract_id.contract_venues, record.id)
                record.date_begin = record.reference_contract_id.date_begin
                record.date_end = record.reference_contract_id.date_end
                record.tag_ids = record.reference_contract_id.event_tag_ids
                record.seats_max = record.reference_contract_id.seats_max
                record.seats_limited = record.reference_contract_id.seats_limited
                record.user_id = record.reference_contract_id.user_id
                record.op_person_id = record.reference_contract_id.op_person_id
                record.op_person_mobile = record.reference_contract_id.op_person_id.mobile_phone
                record.note = record.reference_contract_id.description
                record.event_company_id = record.reference_contract_id.partner_id
                record.event_company_charger_id = record.reference_contract_id.partner_charger_id
                record.event_company_charger_phone = record.reference_contract_id.partner_charger_phone
                record.event_company_charger_mobile = record.reference_contract_id.partner_charger_mobile

                return record.event_event_venues

            else:
                record.name = ''
                record.date_begin = fields.Datetime.now().replace(second=0, microsecond=0) + timedelta(
                    minutes=-fields.Datetime.now().minute % 30)
                record.date_end = record.date_begin + timedelta(days=1)
                record.event_location_id = False
                record.event_event_venues = False
                record.tag_ids = False
                record.seats_max = 0
                record.seats_limited = False
                record.op_person_id = self._get_employee()
                record.user_id = self.env.user
                record.note = False
                record.event_company_id = False
                record.event_company_charger_id = False
                record.event_company_charger_phone = False
                record.event_company_charger_mobile = False

                return False

    @api.onchange('contract_visible')
    def _onchange_contract_visible(self):
        for record in self:
            _logger.info(f"_onchange_contract_visible record.contract_visible={record.contract_visible}")
            if not record.contract_visible:
                record.reference_contract_id = False
            self._compute_contract_info()
            self._compute_date_editable()
            return {'value': {'event_event_venues': record.event_event_venues}}

    @api.model
    def _get_employee(self):
        # 获取当前登录用户的employee记录
        user = self.env.user
        if user.employee_ids:
            return user.employee_ids[0].id  # 返回第一个employee记录ID
        else:
            return False  # 如果没有employee记录，则返回False

    def check_contract_in_use(self, reference_contract_id, event_id):
        domain = [('reference_contract_id', '=', reference_contract_id), ('active', '=', True), ('id', '!=', event_id)]
        contract_in_use = self.env['event.event'].search(domain).mapped('name')
        return contract_in_use

    @api.model
    def check_and_write(self, values):
        """Custom logic to check user permissions before writing."""
        # self.ensure_one()
        tgt_contract_id = ''
        for record in self:
            tgt_contract_id = record.reference_contract_id.id
            _logger.info(f"tgt_contract_id in record={record.reference_contract_id}")

        # 如果values里有
        if 'reference_contract_id' in values:
            tgt_contract_id = values['reference_contract_id']
            _logger.info(f"tgt_contract_id in values={tgt_contract_id}")

        if tgt_contract_id:
            _logger.info(f"tgt_contract_id={tgt_contract_id}")
            # 再次获取合同相关信息
            values['event_event_venues'] = self._get_event_event_venues_from_contract(tgt_contract_id, self.ids[0])
            _logger.info(f"values in check_and_write={values}")

            contract_list = self.check_contract_in_use(tgt_contract_id, self.ids[0])
            if contract_list and len(contract_list) > 0:
                raise AccessError(f"本合同已关联至以下活动。若继续引用本合同，需先将这些活动归档：{contract_list}")

        #     # 检查当前用户是否属于特定权限组，例如event_supervisor
        # if self.env.user.has_group('event_extend.group_event_supervisor') or (
        #         self._origin and 'cron' in self._origin._name):
        #     # 活动审批人仅可以操作“待审批→已审批”的流程
        #
        #     return super(EventEvent, self).write(values)
        # else:
        #     # 如果用户无权更改状态，可以抛出错误或采取其他措施
        #     raise AccessError(f"{self.env.user}您不能直接修改活动状态！请联系活动审批组进行审批！")

    @api.model
    def create(self, vals_list):
        _logger.info(f"vals_list={vals_list}")
        reference_contract_id = ""
        if 'reference_contract_id' in vals_list:
            if vals_list['reference_contract_id']:
                reference_contract_id = vals_list['reference_contract_id']
                contract_list = self.check_contract_in_use(reference_contract_id, 0)
                if contract_list and len(contract_list) > 0:
                    raise AccessError(f"本合同已关联至以下活动。若继续引用本合同，需先将这些活动归档：{contract_list}")

        if 'event_event_venues' in vals_list:
            self._check_event_venues_schedule_create(vals_list['event_event_venues'], reference_contract_id)

        return super().create(vals_list)

    def write(self, values):

        _logger.info(f"before check_and_write values={values}")

        for record in self:
            _logger.info(f"record.event_event_venues len={len(record.event_event_venues)}")
            _logger.info(f"record.event_event_venues={record.event_event_venues}")

        self.check_and_write(values)
        _logger.info(f"before write values={values}")

        reference_contract_id = ""
        if 'reference_contract_id' in values:
            reference_contract_id = values['reference_contract_id']
            _logger.info(f"reference_contract_id={reference_contract_id}")

        if 'event_event_venues' in values:
            self._check_event_venues_schedule_write(values['event_event_venues'], reference_contract_id)

        write_res = super(EventEvent, self).write(values)

        return write_res

    def action_print_venue_application(self):
        return self.env.ref('event_extend.action_print_venue_application').report_action(self)

    def action_print_entry_exit_form(self):
        return self.env.ref('event_extend.action_print_entry_exit_form').report_action(self)

    def _get_event_event_venues_from_contract(self, tgt_contract_id, self_event_id):

        contract_venues = self.env['operation.contract.venues'].search(
            [('operation_contract_id', '=', tgt_contract_id)])
        event_venues = self._set_event_venues_from_contract_venues(contract_venues, self_event_id)
        _logger.info(f"event_venues from contract={event_venues}")
        return event_venues

    def _set_event_venues_from_contract_venues(self, contract_venues, event_id):
        new_event_venues = []
        old_event_venues = self.env['event.event.venues'].search([('event_event_id', '=', event_id)])
        for old_event_venue in old_event_venues:
            new_event_venues.append((2, old_event_venue.id, 0))

        for contract_venue in contract_venues:
            new_event_venues.append((0, 0, {
                'event_event_id': event_id,
                'event_venue_id': contract_venue.contract_venue_id.id,
                'sequence': contract_venue.sequence,
                'event_venue_date_begin': contract_venue.venue_date_begin,
                'event_venue_date_end': contract_venue.venue_date_end,
            }))
        _logger.info(f"event_venues from contract={new_event_venues}")
        return new_event_venues

    def _check_event_venues_schedule_create(self, event_venues_tgt, contract_id):
        for event_venue_tgt in event_venues_tgt:
            _logger.info(f"event_venue_tgt={event_venue_tgt}")
            if event_venue_tgt[2]['event_event_id']:
                event_venues = self.env['event.event.venues'].search([
                    ('event_venue_id', '=', event_venue_tgt[2]['event_venue_id']),
                    ('event_event_id', '!=', event_venue_tgt[2]['event_event_id'])])
            else:
                event_venues = self.env['event.event.venues'].search([
                    ('event_venue_id', '=', event_venue_tgt[2]['event_venue_id'])])

            contract_venues = self._select_contract_venues(contract_id, event_venue_tgt[2]['event_venue_id'])

            self._date_conflict_check(event_venue_tgt, event_venues, contract_venues)

    def _check_event_venues_schedule_write(self, param, ref_contract_id):

        for event_venue_tgt in param:
            _logger.info(f"event_venue_tgt={event_venue_tgt}")
            if event_venue_tgt[0] == 0:  # create
                self._check_event_venues_schedule_create([event_venue_tgt], ref_contract_id)
            elif event_venue_tgt[0] == 1:  # update，要看update对象的venue与该其他行的venue的冲突情况
                this_venue = self.env['event.event.venues'].search([('id', '=', event_venue_tgt[1])])
                event_venues = self.env['event.event.venues'].search(
                    [('event_venue_id', '=', this_venue[0].event_venue_id.id)])

                contract_venues = self._select_contract_venues(ref_contract_id, this_venue[0].event_venue_id.id)

                self._date_conflict_check(event_venue_tgt, event_venues, contract_venues)

    def _date_conflict_check(self, event_venue_tgt, event_venues, contract_venues):
        venues_conflict = []
        _logger.info(f"event_venue_tgt={event_venue_tgt}")
        _logger.info(f"event_venues={event_venues}")
        _logger.info(f"contract_venues={contract_venues}")
        for venue in event_venues:
            date_begin = datetime.strptime(event_venue_tgt[2]['event_venue_date_begin'], '%Y-%m-%d %H:%M:%S')
            date_end = datetime.strptime(event_venue_tgt[2]['event_venue_date_end'], '%Y-%m-%d %H:%M:%S')
            if date_begin <= venue.event_venue_date_begin <= date_end \
                    or venue.event_venue_date_begin <= date_begin <= venue.event_venue_date_end:
                venues_conflict.append({
                    'event_venue_tgt': event_venue_tgt,
                    'venue_db': venue,
                    'model_name': 'event_venue',
                })

        for contract_venue in contract_venues:
            date_begin = datetime.strptime(event_venue_tgt[2]['event_venue_date_begin'], '%Y-%m-%d %H:%M:%S')
            date_end = datetime.strptime(event_venue_tgt[2]['event_venue_date_end'], '%Y-%m-%d %H:%M:%S')
            if date_begin <= contract_venue.venue_date_begin <= date_end \
                    or contract_venue.venue_date_begin <= date_begin <= contract_venue.venue_date_end:
                venues_conflict.append({
                    'event_venue_tgt': event_venue_tgt,
                    'venue_db': contract_venue,
                    'model_name': 'contract_venue',
                })

        if venues_conflict:
            user_tz = self._context.get('tz') or self.env.user.partner_id.tz or 'Asia/Shanghai'
            self_tz = self.with_context(tz=user_tz)
            warn_msg = ["以下活动地点排期冲突！请确认："]
            for venue_ille in venues_conflict:
                db_date_s = fields.Datetime.context_timestamp(
                    self_tz, venue_ille['venue_db'].event_venue_date_begin if
                    venue_ille['model_name'] == 'event_venue' else
                    venue_ille['venue_db'].venue_date_begin)
                date_s = db_date_s.strftime('%Y-%m-%d %H:%M:%S')
                db_date_e = fields.Datetime.context_timestamp(
                    self_tz, venue_ille['venue_db'].event_venue_date_end if
                    venue_ille['model_name'] == 'event_venue' else
                    venue_ille['venue_db'].venue_date_end)
                date_e = db_date_e.strftime('%Y-%m-%d %H:%M:%S')
                warn_msg.append("【")
                warn_msg.append(venue_ille['venue_db'].event_venue_id.name if
                                venue_ille['model_name'] == 'event_venue' else
                                venue_ille['venue_db'].contract_venue_id.name)
                warn_msg.append("：")
                warn_msg.append(date_s + "至" + date_e)
                warn_msg.append("（活动名：" if venue_ille['model_name'] == 'event_venue' else "（合同名：")
                warn_msg.append(venue_ille['venue_db'].event_event_id.name if
                                venue_ille['model_name'] == 'event_venue' else
                                venue_ille['venue_db'].operation_contract_id.name)
                warn_msg.append("）】")

            raise UserError(warn_msg)

    def _select_contract_venues(self, contract_id, event_venue_id):
        if contract_id:
            contract_venues = self.env['operation.contract.venues'].search([
                ('contract_venue_id', '=', event_venue_id),
                ('operation_contract_id', '!=', contract_id)])
        else:
            contract_venues = self.env['operation.contract.venues'].search([
                ('contract_venue_id', '=', event_venue_id)])
        return contract_venues
