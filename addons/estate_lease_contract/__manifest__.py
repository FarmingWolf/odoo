# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "资产租赁合同管理",
    'version': '0.0.2',
    'depends': ['base', 'web', 'utils', 'estate', 'parking'],
    'summary': '资产租赁合同管理',
    'category': 'Real Estate/Lease Contract',
    'website': 'https://www.odoo.com/app/realestate',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/estate.lease.contract.rental.business.type.csv',
        'security/estate.lease.contract.rental.main.category.csv',

        'views/estate_lease_contract_bank_account_views.xml',
        'views/estate_lease_contract_incentives_views.xml',
        'views/estate_lease_contract_property_views.xml',
        'views/estate_lease_contract_tag_views.xml',
        'views/estate_lease_contract_rental_business_type_views.xml',
        'views/estate_lease_contract_rental_main_category_views.xml',
        'views/estate_lease_contract_rental_turnover_percentage_views.xml',
        'views/estate_lease_contract_rental_period_percentage_views.xml',
        'views/estate_lease_contract_property_management_fee_plan_views.xml',
        'views/estate_lease_contract_rental_plan_views.xml',
        'views/estate_lease_contract_views.xml',
        'views/estate_lease_contract_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'estate_lease_contract/static/src/**/*',
            # 'estate_lease_contract/static/src/css/estate_lease_contract.scss',
            # 'estate_lease_contract/static/src/js/estate_lease_contract_events.js',
            'estate_lease_contract/static/src/js/estate_lease_contract_rental_plan_load.js',
        ],
    },
    'license': 'AGPL-3'
}
