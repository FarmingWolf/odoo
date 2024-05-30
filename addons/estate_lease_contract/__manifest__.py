# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "资产租赁合同管理",
    'depends': ['base', 'web', 'estate'],
    'summary': '资产租赁合同管理',
    'category': '合同/资产租赁合同管理',
    'website': 'https://www.odoo.com/app/realestate',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/estate_lease_contract_menus.xml',
        'views/estate_lease_contract_rental_plan_views.xml',
        'views/estate_lease_contract_tag_views.xml',
        'views/estate_lease_contract_type_views.xml',
        'views/estate_lease_contract_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate_lease_contract/static/src/css/estate_lease_contract.scss',
        ],
    }
}
