# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from datetime import date, timedelta


class EstateAreaReport(models.Model):
    _name = "estate.area.report"
    _auto = False
    _description = "Estate Area Analysis"

    id = fields.Integer(string='id')
    property_id = fields.Many2one('estate.property', string="资产（房屋）")
    property_rent_area = fields.Float(string="计租面积")
    property_state = fields.Char(string='资产状态')
    property_type_id = fields.Many2one('estate.property.type', string='资产类型')
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    def _select(self):
        return """
            SELECT
                t.id,
                t.property_id,
                t.property_rent_area,
                CASE WHEN t.property_state = '已租' THEN '已租' ELSE '空置' END as property_state,
                t.company_id,
                e_p.property_type_id
        """

    def _from(self):
        return """
            FROM estate_lease_contract_property_daily_status AS t
        """

    def _join(self):
        return """
            JOIN estate_property AS e_p ON e_p.id = t.property_id
            LEFT JOIN estate_property_type AS e_p_t ON e_p_t.id = e_p.property_type_id
        """

    def _where(self):
        return f"""
            WHERE
                t.status_date = '{date.today() + timedelta(days=-1)}'
            AND (e_p_t.count_ratio_as_room = true 
                or e_p_t.count_ratio_as_room is null)
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._join(), self._where())
                         )
