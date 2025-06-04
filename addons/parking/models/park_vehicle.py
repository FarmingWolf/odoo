# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from addons.utils.models.utils import Utils, _logger
from odoo import _, api, fields, models
from odoo.osv import expression


class ParkVehicle(models.Model):
    _name = 'park.vehicle'
    _inherit = 'fleet.vehicle'
    _description = 'Park Vehicle'
    _order = 'name asc'

    name = fields.Char(compute="_compute_vehicle_name", store=True)
    driver_id = fields.Many2one('res.partner', 'Vehicle Owner', tracking=True, copy=False)
    future_driver_id = fields.Many2one('res.partner', 'Driver', tracking=True, copy=False, check_company=True)

    driver_phone = fields.Char(related="driver_id.phone", string="Owner Phone", copy=False)
    driver_mobile = fields.Char(related="driver_id.mobile", string="Owner Mobile", copy=False)
    future_driver_phone = fields.Char(related="future_driver_id.phone", string="Driver Phone", copy=False)
    future_driver_mobile = fields.Char(related="future_driver_id.mobile", string="Driver Mobile", copy=False)
    model_id = fields.Many2one('park.vehicle.model', 'Model', tracking=True, required=True)
    brand_id = fields.Many2one('park.vehicle.model.brand', 'Brand', related="model_id.brand_id", store=True, readonly=False)

    log_assignments = fields.One2many('park.vehicle.assignation.log', 'vehicle_id', string='Assignment Logs')
    log_services = fields.One2many('park.vehicle.log.services', 'vehicle_id', 'Services Logs')
    log_contracts = fields.One2many('park.vehicle.log.contract', 'vehicle_id', 'Contracts')

    latest_assignment = fields.Many2one('park.vehicle.assignation.log', 'Latest Assignment',
                                        compute='_compute_latest_assignment', readonly=True, store=True)
    latest_lease_contract = fields.Char('Latest Lease Contract',related="latest_assignment.lease_contract_nm", store=True)
    latest_lease_contract_id = fields.Integer('Latest Lease Contract ID',related="latest_assignment.lease_contract_id", store=True)
    latest_parking_space = fields.Many2one('parking.space', string="Latest Parking Space",
                                           related="latest_assignment.parking_space_id", store=True)
    latest_date_start = fields.Date(string="Latest Start Date", related="latest_assignment.date_start", store=True, readonly=False)
    latest_date_end = fields.Date(string="Latest End Date", related="latest_assignment.date_end", store=True, readonly=False)

    contract_count = fields.Integer(compute="_compute_count_all", string='Contract Count')
    service_count = fields.Integer(compute="_compute_count_all", string='Services')
    history_count = fields.Integer(compute="_compute_count_all", string="Drivers History Count")
    tag_ids = fields.Many2many('park.vehicle.tag', 'park_vehicle_vehicle_tag_rel', 'vehicle_tag_id', 'tag_id', 'Tags',
                               copy=False)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    category_id = fields.Many2one('park.vehicle.model.category', 'Category', compute='_compute_model_fields',
                                  store=True, readonly=False)

    acquisition_date = fields.Date('Record Date', required=False, default=fields.Date.today, help='Date of vehicle record')

    @api.depends('log_assignments')
    def _compute_latest_assignment(self):
        for record in self:
            if record.log_assignments:
                record.latest_assignment = Utils.find_closest_date_object(record.log_assignments, fields.Date.today(),
                                                                          start_date_key="date_start",
                                                                          end_date_key="date_end")

    @api.depends('model_id.brand_id.name', 'model_id.name', 'license_plate')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = ((record.license_plate or _('No Plate')) + '/' + (record.driver_id.name or '') + '/' +
                           (record.driver_mobile or record.driver_phone or '') + '/' +
                           (record.model_id.brand_id.name or '') + '/' + (record.model_id.name or ''))

    def _get_default_state(self):
        state = self.env.ref('parking.park_vehicle_state_new_request', raise_if_not_found=False)
        return state if state and state.id else False

    state_id = fields.Many2one('park.vehicle.state', 'State',
        default=_get_default_state, group_expand='_read_group_stage_ids', tracking=True, store=True,
        help='Current state of the vehicle', ondelete="set null", compute='_compute_state_id')

    @api.depends('log_assignments', 'latest_assignment')
    def _compute_state_id(self):
        for record in self:
            if record.latest_assignment:
                today = fields.Date.today()
                tgt_state_str = 'parking.park_vehicle_state_new_request'
                if today < record.latest_assignment.date_start:
                    tgt_state_str = 'parking.park_vehicle_state_registered'
                elif record.latest_assignment.date_start <= today <= record.latest_assignment.date_end:
                    tgt_state_str = 'parking.park_vehicle_state_effective'
                else:
                    tgt_state_str = 'parking.park_vehicle_state_outdated'

                state = self.env.ref(tgt_state_str, raise_if_not_found=False)
                record.state_id = state if state and state.id else False
            else:
                record.state_id = record._get_default_state()


    def _compute_count_all(self):
        LogService = self.env['park.vehicle.log.services'].with_context(active_test=False)
        LogContract = self.env['park.vehicle.log.contract'].with_context(active_test=False)
        History = self.env['park.vehicle.assignation.log']
        services_data = LogService._read_group([('vehicle_id', 'in', self.ids)], ['vehicle_id', 'active'], ['__count'])
        logs_data = LogContract._read_group([('vehicle_id', 'in', self.ids), ('state', '!=', 'closed')], ['vehicle_id', 'active'], ['__count'])
        histories_data = History._read_group([('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['__count'])

        mapped_service_data = defaultdict(lambda: defaultdict(lambda: 0))
        mapped_log_data = defaultdict(lambda: defaultdict(lambda: 0))
        mapped_history_data = defaultdict(lambda: 0)

        for vehicle, active, count in services_data:
            mapped_service_data[vehicle.id][active] = count
        for vehicle, active, count in logs_data:
            mapped_log_data[vehicle.id][active] = count
        for vehicle, count in histories_data:
            mapped_history_data[vehicle.id] = count

        for vehicle in self:
            vehicle.service_count = mapped_service_data[vehicle.id][vehicle.active]
            vehicle.contract_count = mapped_log_data[vehicle.id][vehicle.active]
            vehicle.history_count = mapped_history_data[vehicle.id]

    @api.depends('log_contracts')
    def _compute_contract_reminder(self):
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        for record in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            state = ''
            for element in record.log_contracts:
                if element.state in ('open', 'expired') and element.expiration_date:
                    current_date_str = fields.Date.context_today(record)
                    due_time_str = element.expiration_date
                    current_date = fields.Date.from_string(current_date_str)
                    due_time = fields.Date.from_string(due_time_str)
                    diff_time = (due_time - current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < delay_alert_contract:
                        due_soon = True
                        total += 1
                    if overdue or due_soon:
                        log_contract = self.env['park.vehicle.log.contract'].search([
                            ('vehicle_id', '=', record.id),
                            ('state', 'in', ('open', 'expired'))
                            ], limit=1, order='expiration_date asc')
                        if log_contract:
                            # we display only the name of the oldest overdue/due soon contract
                            name = log_contract.name
                            state = log_contract.state

            record.contract_renewal_overdue = overdue
            record.contract_renewal_due_soon = due_soon
            record.contract_renewal_total = total - 1  # we remove 1 from the real total for display purposes
            record.contract_renewal_name = name
            record.contract_state = state

    def _search_contract_renewal_due_soon(self, operator, value):
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        res = []
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        datetime_today = fields.Datetime.from_string(today)
        limit_date = fields.Datetime.to_string(datetime_today + relativedelta(days=+delay_alert_contract))
        res_ids = self.env['park.vehicle.log.contract'].search([
            ('expiration_date', '>', today),
            ('expiration_date', '<', limit_date),
            ('state', 'in', ['open', 'expired'])
        ]).mapped('vehicle_id').ids
        res.append(('id', search_operator, res_ids))
        return res

    def _search_get_overdue_contract_reminder(self, operator, value):
        res = []
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        res_ids = self.env['park.vehicle.log.contract'].search([
            ('expiration_date', '!=', False),
            ('expiration_date', '<', today),
            ('state', 'in', ['open', 'expired'])
        ]).mapped('vehicle_id').ids
        res.append(('id', search_operator, res_ids))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        ptc_values = [self._clean_vals_internal_user(vals) for vals in vals_list]
        vehicles = super().create(vals_list)
        for vehicle, vals, ptc_value in zip(vehicles, vals_list, ptc_values):
            if ptc_value:
                vehicle.sudo().write(ptc_value)
            if 'driver_id' in vals and vals['driver_id']:
                vehicle.create_driver_history(vals)
            if 'future_driver_id' in vals and vals['future_driver_id']:
                state_waiting_list = self.env.ref('parking.park_vehicle_state_waiting_list',
                                                  raise_if_not_found=False)
                states = vehicle.mapped('state_id').ids
                if not state_waiting_list or state_waiting_list.id not in states:
                    future_driver = self.env['res.partner'].browse(vals['future_driver_id'])
                    if self.vehicle_type == 'bike':
                        future_driver.sudo().write({'plan_to_change_bike': True})
                    if self.vehicle_type == 'car':
                        future_driver.sudo().write({'plan_to_change_car': True})
        return vehicles

    def write(self, vals):
        if 'driver_id' in vals and vals['driver_id']:
            driver_id = vals['driver_id']
            for vehicle in self.filtered(lambda v: v.driver_id.id != driver_id):
                vehicle.create_driver_history(vals)
                if vehicle.driver_id:
                    vehicle.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=vehicle.manager_id.id or self.env.user.id,
                        note=_('Specify the End date of %s', vehicle.driver_id.name))

        if 'future_driver_id' in vals and vals['future_driver_id']:
            state_waiting_list = self.env.ref('parking.park_vehicle_state_waiting_list',
                                              raise_if_not_found=False)
            states = self.mapped('state_id').ids if 'state_id' not in vals else [vals['state_id']]
            if not state_waiting_list or state_waiting_list.id not in states:
                future_driver = self.env['res.partner'].browse(vals['future_driver_id'])
                if self.vehicle_type == 'bike':
                    future_driver.sudo().write({'plan_to_change_bike': True})
                if self.vehicle_type == 'car':
                    future_driver.sudo().write({'plan_to_change_car': True})

        if 'active' in vals and not vals['active']:
            self.env['park.vehicle.log.contract'].search([('vehicle_id', 'in', self.ids)]).active = False
            self.env['park.vehicle.log.services'].search([('vehicle_id', 'in', self.ids)]).active = False

        su_vals = self._clean_vals_internal_user(vals)
        if su_vals:
            self.sudo().write(su_vals)
        res = super().write(vals)
        return res

    def _get_driver_history_data(self, vals):
        self.ensure_one()
        return {
            'vehicle_id': self.id,
            'driver_id': vals['driver_id'],
            'date_start': fields.Date.today(),
            'date_end': fields.Date.today(),
        }

    def create_driver_history(self, vals):
        for vehicle in self:
            pass  # todo
            # self.env['park.vehicle.assignation.log'].create(
            #     vehicle._get_driver_history_data(vals),
            # )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['park.vehicle.state'].search([], order=order)

    def act_show_log_cost(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        copy_context = dict(self.env.context)
        copy_context.pop('group_by', None)
        res = self.env['ir.actions.act_window']._for_xml_id('parking.park_vehicle_costs_action')
        res.update(
            context=dict(copy_context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        return res

    def open_assignation_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assignment Logs',
            'view_mode': 'tree',
            'res_model': 'park.vehicle.assignation.log',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_driver_id': self.driver_id.id, 'default_vehicle_id': self.id}
        }
