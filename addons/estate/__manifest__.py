# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "资产管理",
    'depends': ['base', 'web'],
    'summary': '资产租赁、合同管理等等',
    'category': 'Real Estate/Brokerage',
    'website': 'https://www.odoo.com/app/realestate',
    'installable': True,
    'application': True,
    'auto_install': False,
    'version': '2.11',
    'data': [
        'security/security.xml',
        'security/ir.rule.csv',
        'security/ir.rule.xml',
        'security/ir.model.access.csv',
        'security/estate.property.type.csv',
        'security/estate.property.tag.csv',

        'views/estate_property_sales_person_views.xml',
        'views/estate_property_type_views.xml',
        'views/estate_property_tag_views.xml',
        'views/estate_property_offer_views.xml',
        'views/estate_property_views.xml',
        'views/estate_menus.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate/static/src/css/estate_property.css',
        ],
    },
    'license': 'AGPL-3'
}
