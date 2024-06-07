# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class EstateLeaseContractRentalTurnoverPercentage(models.Model):
    """
    从0到以上抽成比例为6%
    从0到666666.67抽成比例为7%;从666666.67到以上抽成比例为7%
    从0到1000000抽成比例为6%;从1000000到以上抽成比例为6%
    从0到以上抽成比例为11%
    从0到666666.67抽成比例为8%;从666666.67到以上抽成比例为8%
    从0到666666.67抽成比例为6%;从1000000到1250000抽成比例为7.5%;从1250000到以上抽成比例为8%;从666666.67到833333.33抽成比例为6.5%;从833333.33到1000000抽成比例为7%
    从0到665000抽成比例为7%;从665000到以上抽成比例为8%
    从0到以上抽成比例为9%
    从0到900000抽成比例为7%;从900000到以上抽成比例为8%
    从0到666666.67抽成比例为6%;从1000000到1250000抽成比例为7.5%;从1250000到以上抽成比例为8%;从666666.67到833333.34抽成比例为6.5%;从833333.34到1000000抽成比例为7%
    从0到666667抽成比例为7%;从666667到以上抽成比例为7%
    从0到300001抽成比例为9%;从300001到以上抽成比例为9%
    从0到666666.67抽成比例为6%;从666666.67到以上抽成比例为6%
    从0到666667抽成比例为7%;从666667到以上抽成比例为8%
    从0到260001抽成比例为9%;从260001到以上抽成比例为9%
    从0到265001抽成比例为9%;从265001到以上抽成比例为9%
    ……其他可自定义
    """
    _name = "estate.lease.contract.rental.turnover.percentage"
    _description = "营业额抽成比例设置"
    _order = "sequence"

    name = fields.Char('抽成设置名', required=True)
    sequence = fields.Integer('排序', default=1)
    turnover_type = fields.Selection(string='营业额种类',
                                     selection=[('net_turnover', '净营业额'), ('after_tax', '税后营业额'),
                                                ('total_turnover', '总营业额')], )

    percentage_from = fields.Float(default=0.0, string="抽成比例（最低）")
    percentage_to = fields.Float(default=0.0, string="抽成比例（最高）")
    turnover_from = fields.Float(default=0.0, string="营业额（元）从（>=）")
    turnover_to = fields.Float(default=0.0, string="营业额（元）到（<）")
    percentage = fields.Float(default=0.0, string="抽成比例（%）")
    name_description = fields.Char(string="抽成比例描述", readonly=True, compute="_combine_description")

    _sql_constraints = [
        ('name', 'unique(turnover_type, turnover_from, turnover_to, percentage)', '相同营业额范围，相同抽成比例已存在')
    ]

    @api.depends("turnover_type")
    def _get_display_value(self):
        field_info = self.env['ir.model.fields'].search_read(
            [('model', '=', self._name), ('name', '=', 'turnover_type')],
            ['selection']
        )

        if field_info and 'selection' in field_info[0]:
            selection_options_str = field_info[0]['selection']
            selection_options = ast.literal_eval(selection_options_str)

            for record in self:
                for key, value in selection_options:
                    if key == record.turnover_type:
                        return value
                return False

    # turnover_type_display = fields.Char(string='营业额种类显示值', compute='_get_display_value')

    @api.depends("turnover_type", "turnover_from", "turnover_to", "percentage")
    def _combine_description(self):
        for record in self:
            record.name_description = "{3}从{0}元（不含）到{1}元（含）抽成比例为{2}%".format(record.turnover_from,
                                                                             record.turnover_to,
                                                                             record.percentage,
                                                                             self._get_display_value())

    @api.constrains("turnover_from", "turnover_to", "percentage", "percentage_from", "percentage_to")
    def _check_input(self):
        for record in self:
            if float_compare(record.percentage_to, record.percentage_from, 2) < 0:
                raise ValidationError("【抽成比例（最高）】应不低于【抽成比例（最低）】")
            if float_compare(record.percentage_to, record.percentage, 2) < 0:
                raise ValidationError("【抽成比例（%）】应不高于【抽成比例（最高）】")
            if float_compare(record.percentage, record.percentage_from, 2) < 0:
                raise ValidationError("【抽成比例（%）】应不低于【抽成比例（最低）】")
            if float_compare(record.turnover_to, record.turnover_from, 2) < 0:
                raise ValidationError("【营业额（元）到（<）】应不低于【营业额（元）从（>=）】")
