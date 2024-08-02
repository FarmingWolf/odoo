# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "日常业务事项管理",
    'version': '0.1',
    'depends': ['base'],
    'category': 'Accounting/业务事项',
    'summary': '分组设置日常业务事项',
    'author': '491Tech',
    'website': 'https://www.odoo.com/',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/business_items_views.xml',
    ],
    'assets': {
    },
    'license': 'AGPL-3'
}
