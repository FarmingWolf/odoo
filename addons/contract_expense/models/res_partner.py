# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
from markupsafe import Markup
import werkzeug

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
from odoo.tools import email_split, float_repr, float_round, is_html_empty

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _description = '继承partner'
    _inherit = 'res.partner'

    @api.model
    def create(self, vals_list):
        # 设置res.partner的创建人所属company_id
        if 'company_id' in vals_list:
            if not vals_list['company_id']:
                vals_list['company_id'] = self.env.user.company_id.id

        return super().create(vals_list)

    @api.model
    def name_create(self, name):
        """复写此方法为了能把company_id写库"""
        partner_id, display_name = super().name_create(name)
        _logger.debug(f"self.env.user.company_id={self.env.user.company_id}")
        self.env['res.partner'].search([('id', '=', partner_id)]).write({'company_id': self.env.user.company_id.id})

        return partner_id, display_name
