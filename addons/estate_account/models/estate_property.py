# -*- coding: utf-8 -*-

from odoo import models

class EstateProperty(models.Model):
    _inherit = "estate.property"

    def action_sold_property(self):
        print("calling super action_sold_property")

        print("暂时不用发票逻辑")
        # 暂时不用发票逻辑
        return super(EstateProperty, self).action_sold_property()

        # 新增步骤：创建发票
        for property in self:
            # 获取当前estate.property的partner_id
            partner_id = property.sales_person_id.id
            selling_price = property.selling_price

            # 计算6%的销售价格
            percentage_amount = (selling_price * 6) / 100.0

            # 准备创建invoice（account.move）所需的values字典
            invoice_values = {
                'move_type': 'out_invoice',  # 对应于'Customer Invoice'
                'partner_id': partner_id,  # 设置合作伙伴为客户
                # 根据需要添加更多字段，如产品、金额等
                'invoice_line_ids': [
                    (0, 0, {  # 创建新行
                        'name': '销售佣金 (6%)',
                        'quantity': 1,
                        'price_unit': percentage_amount,
                    }),
                    (0, 0, {  # 第二行
                        'name': '管理费',
                        'quantity': 1,
                        'price_unit': 100.00,
                    }),
                ],
            }

            # 使用env来创建account.move记录
            invoice = self.env['account.move'].create(invoice_values)

        return super(EstateProperty, self).action_sold_property()
