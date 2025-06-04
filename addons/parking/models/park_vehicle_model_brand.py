# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ParkVehicleModelBrand(models.Model):
    _name = 'park.vehicle.model.brand'
    _inherit = 'fleet.vehicle.model.brand'

    _description = '车辆品牌（制造商）'
    _order = 'name asc'

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    model_ids = fields.One2many('park.vehicle.model', 'brand_id')

    @api.depends('model_ids')
    def _compute_model_count(self):
        model_data = self.env['park.vehicle.model']._read_group([
            ('brand_id', 'in', self.ids),
        ], ['brand_id'], ['__count'])
        models_brand = {brand.id: count for brand, count in model_data}

        for record in self:
            record.model_count = models_brand.get(record.id, 0)

    def action_brand_model(self):
        self.ensure_one()
        view = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'park.vehicle.model',
            'name': 'Models',
            'context': {'search_default_brand_id': self.id, 'default_brand_id': self.id}
        }

        return view
