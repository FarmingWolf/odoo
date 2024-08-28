# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "注册地址管理",
    'depends': ['base', 'web'],
    'summary': '为租赁合同分配的注册地址管理等等',
    'category': 'Real Estate/Brokerage',
    'website': 'https://www.odoo.com/app/realestate',
    'installable': True,
    'application': True,
    'auto_install': False,
    'version': '0.01',
    'data': [
        'security/security.xml',
        'security/ir.rule.csv',
        'security/ir.model.access.csv',

        'views/estate_registration_addr_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
    'license': 'AGPL-3'
}
