# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "停车位管理",
    'depends': ['base', 'web', 'fleet'],
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
        'views/park_vehicle_model_views.xml',
        'views/park_vehicle_views.xml',
        'views/parking_space_vehicle_rel_views.xml',
        'views/park_vehicle_assignation_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/parking_menus.xml',

        'data/park_cars_data.xml',
        'data/park_data.xml',
    ],
    'demo': ['data/park_demo.xml'],
    'assets': {
        'web.assets_backend': [
            'parking/static/src/css/parking.scss',
            'parking/static/src/**/*',
        ],
    },
    'license': 'AGPL-3'
}
