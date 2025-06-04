# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models


class ParkVehicleModel(models.Model):
    _name = 'park.vehicle.model'
    _inherit = 'fleet.vehicle.model'
    _description = '车辆型号'
    _order = 'name asc'


    vendors = fields.Many2many('res.partner', 'park_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    brand_id = fields.Many2one('park.vehicle.model.brand', 'Manufacturer', required=True)
    category_id = fields.Many2one('park.vehicle.model.category', 'Category')

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    def _compute_vehicle_count(self):
        group = self.env['park.vehicle']._read_group(
            [('model_id', 'in', self.ids)], ['model_id'], aggregates=['__count'],
        )
        count_by_model = {model.id: count for model, count in group}
        for model in self:
            model.vehicle_count = count_by_model.get(model.id, 0)

    @api.model
    def _search_vehicle_count(self, operator, value):
        if operator not in ['=', '!=', '<', '>'] or not isinstance(value, int):
            raise NotImplementedError(_('Operation not supported.'))
        fleet_models = self.env['park.vehicle.model'].search([])
        if operator == '=':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count == value)
        elif operator == '!=':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count != value)
        elif operator == '<':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count < value)
        elif operator == '>':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count > value)
        return [('id', 'in', fleet_models.ids)]

    def action_model_vehicle(self):
        self.ensure_one()
        view = {
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'park.vehicle',
            'name': _('Vehicles'),
            'context': {'search_default_model_id': self.id, 'default_model_id': self.id}
        }

        return view
