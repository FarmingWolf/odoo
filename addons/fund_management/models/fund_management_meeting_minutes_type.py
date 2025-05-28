# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class FundManagementMeetingMinutesType(models.Model):

    _name = "fund.management.meeting.minutes.type"
    _description = "Meeting minutes type"
    _order = "sequence ASC"

    name = fields.Char(string='Meeting Minutes Type', required=True,
                       help="Please do not include spaces in the category name")
    sequence = fields.Integer(string="Sequence", required=True, default=0, copy=False)
    color = fields.Integer()
    active = fields.Boolean(default=True)
    mandatory = fields.Boolean(string="Mandatory", default=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
    editable = fields.Boolean(default=lambda self: self._compute_editable(), compute='_compute_editable')

    def _compute_editable(self):
        ret_editable = self.env.user.has_group('fund_management.group_fund_management_manager')
        self.editable = ret_editable
        return ret_editable

    _sql_constraints = [
        ('name', 'unique(name, company_id)', 'Meeting minutes type name duplicated!')
    ]
