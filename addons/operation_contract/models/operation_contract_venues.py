# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, is_html_empty

_logger = logging.getLogger(__name__)


def _compute_date_begin_end(fields_list, default_result):
    if 'venue_date_begin' in fields_list and 'venue_date_begin' not in default_result:
        now = fields.Datetime.now()
        # Round the datetime to the nearest half hour (e.g. 08:17 => 08:30 and 08:37 => 09:00)
        default_result['venue_date_begin'] = now.replace(second=0, microsecond=0) + timedelta(minutes=-now.minute % 30)

    if 'venue_date_end' in fields_list and 'venue_date_end' not in default_result and default_result.get(
            'venue_date_begin'):
        default_result['venue_date_end'] = default_result['venue_date_begin'] + timedelta(days=1)

    return default_result


class OperationContractVenues(models.Model):
    _name = "operation.contract.venues"
    _description = "合同中指定的活动场所及使用时间，三个都是必填字段"
    _order = 'sequence'

    name = fields.Char('合同名称', related="operation_contract_id.name")
    operation_contract_id = fields.Many2one('operation.contract.contract', string='合同')

    contract_venue_id = fields.Many2one('event.track.location', string='活动地点', required=True)
    venue_date_begin = fields.Datetime(string="使用开始时间", required=True)
    venue_date_end = fields.Datetime(string="使用结束时间", required=True)

    @api.model
    def default_get(self, fields_list):
        default_result = super().default_get(fields_list)
        _compute_date_begin_end(fields_list, default_result)
        return default_result

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    sequence = fields.Integer(string='序号', default=_default_sequence)

    _sql_constraints = [("venue_date_s_e_check",
                         "CHECK(venue_date_end > venue_date_begin)", "结束时间必须在开始时间之后！"),
                        ("unique_contract_venue", "unique(operation_contract_id, contract_venue_id)", "活动地点重复")]
