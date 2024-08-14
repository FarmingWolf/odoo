# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "停车位管理",
    'depends': ['base', 'web'],
    'summary': '停车场停车位管理',
    'category': '停车/停车位管理',
    'website': 'https://www.odoo.com/app/realestate',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.csv',

        'views/parking_views.xml',
        'views/parking_lot_views.xml',
        'views/parking_space_views.xml',
        'views/parking_space_type_views.xml',
        'views/parking_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'parking/static/src/css/parking.scss',
        ],
    },
    'license': 'AGPL-3'
}
