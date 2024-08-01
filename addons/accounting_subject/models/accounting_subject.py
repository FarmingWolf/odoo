# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountingSubject(models.Model):
    _name = 'accounting.subject.subject'
    _description = '会计科目'
    _order = 'level, sequence, code, name'

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char(string='科目名', required=True)
    code = fields.Char(string='科目编码', required=True)
    description = fields.Text('描述')
    parent_id = fields.Many2one('accounting.subject.subject', string='父级科目', ondelete='restrict')
    child_ids = fields.One2many('accounting.subject.subject', 'parent_id', string='子科目')
    level = fields.Integer(string='级别', compute='_compute_level', store=True, recursive=True)
    sequence = fields.Integer(string='序号', default=_default_sequence)

    @api.depends('parent_id.level')
    def _compute_level(self):
        for subject in self:
            if subject.parent_id:
                subject.level = subject.parent_id.level + 1
            else:
                subject.level = 0

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive subjects.'))

    def name_get(self):
        res = []
        for subject in self:
            name = subject.name
            if subject.level > 0:
                name = " / ".join([p.name for p in subject._get_all_parents()] + [subject.name])
            res.append((subject.id, name))
        return res

    def _get_all_parents(self):
        self.ensure_one()
        all_parents = self.parent_id
        if self.parent_id:
            all_parents |= self.parent_id._get_all_parents()
        return all_parents

    def _get_children(self):
        """递归获取所有子科目"""
        self.ensure_one()
        children = self.child_ids
        for child in self.child_ids:
            children |= child._get_children()
        return children

    def _update_child_levels(self):
        """当父科目更改时，更新所有子科目的层级"""
        for subject in self:
            children = subject._get_children()
            children._compute_level()

    @api.model
    def create(self, vals):
        subject = super(AccountingSubject, self).create(vals)
        if vals.get('parent_id'):
            subject._update_child_levels()
        return subject

    def write(self, vals):
        if 'parent_id' in vals:
            old_parent_id = self.parent_id
            result = super(AccountingSubject, self).write(vals)
            if old_parent_id != vals['parent_id']:
                self._update_child_levels()
            return result
        return super(AccountingSubject, self).write(vals)

    _sql_constraints = [
        ('name', 'unique(name)', '科目名称不能重复'),
        ('code', 'unique(code)', '科目编码不能重复'),
    ]
