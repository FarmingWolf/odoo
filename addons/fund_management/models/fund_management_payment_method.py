# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import _


class FundManagementPaymentMethod(models.Model):
    """
    网银转账、支票、现金
    """
    _name = "fund.management.payment.method"
    _description = "Payment Method"
    _order = "sequence"

    name = fields.Char('Payment Method', required=True)
    sequence = fields.Integer('sequence', default=1)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    _sql_constraints = [
        ('name', 'unique(name, company_id)', _('The Payment method can not be duplicated'))
    ]
