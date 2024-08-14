# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models


class EventOptionGroup(models.Model):
    _name = "event.option.group"
    _description = "Event Option Group"
    _order = "sequence"

    def _default_sequence(self):
        """
        Here we use a _default method instead of ordering on 'sequence, id' to
        prevent adding a new related stored field in the 'event.option' model that
        would hold the category id.
        """
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char(string="分组名", required=True, translate=True)
    sequence = fields.Integer(string='序号', default=_default_sequence)
    option_ids = fields.One2many('event.option', 'group_id', string="选项")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)


class EventOption(models.Model):
    _name = "event.option"
    _description = "Event Option"
    _order = "group_sequence, sequence, id"

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char("选项名", required=True, translate=True)
    sequence = fields.Integer('序号', default=0)
    group_id = fields.Many2one("event.option.group", string="组别", required=True, ondelete='cascade')
    group_sequence = fields.Integer(related='group_id.sequence', string='分组序号', store=True)
    color = fields.Integer(string='设置颜色', default=lambda self: self._default_color())
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)
