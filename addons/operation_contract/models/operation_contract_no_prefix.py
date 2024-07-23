# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import win32api

from odoo import fields, models


class OperationContractNoPrefix(models.Model):
    _name = 'operation.contract.no.prefix'
    _description = '运营合同号前缀'

    prefix = fields.Char(string='运营合同号前缀', required=True, help='前后空格将被清除，中间空格将被"-"替代')

    def write(self, vals):

        vals['prefix'] = vals['prefix'].lstrip().rstrip().replace(' ', '-')
        res = super(OperationContractNoPrefix, self).write(vals)
        return res
