# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "资产租赁合同管理",
    'version': '0.0.2',
    'depends': ['base', 'web', 'mail', 'utils', 'estate', 'parking', 'estate_registration_addr'],
    'summary': '资产租赁合同管理',
    'category': 'Real Estate/Lease Contract',
    'website': 'https://www.odoo.com/app/realestate',
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'estate_lease_contract/static/src/js/custom_tree_render.js',
            'estate_lease_contract/static/src/xml/custom_tree_render.xml',
            'estate_lease_contract/static/src/js/tree_view_custom.js',
            'estate_lease_contract/static/src/xml/tree_view_custom.xml',
            'estate_lease_contract/static/src/js/estate_lease_contract_property_status_load.js',
            'estate_lease_contract/static/src/js/estate_lease_contract_rental_plan_load.js',
        ],

        'web.report_assets_pdf': [
            '/estate_lease_contract/static/src/css/estate_lease_contract_report.scss',
        ],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/estate.lease.contract.rental.business.type.csv',
        'security/estate.lease.contract.rental.main.category.csv',
        'security/ir.rule.csv',

        'views/estate_lease_contract_bank_account_views.xml',
        'views/estate_lease_contract_party_a_unit_views.xml',
        'views/estate_lease_contract_incentives_views.xml',
        'views/estate_lease_contract_property_rental_detail_views.xml',
        'views/estate_lease_contract_property_views.xml',
        'views/estate_lease_contract_tag_views.xml',
        'views/estate_lease_contract_rental_business_type_views.xml',
        'views/estate_lease_contract_rental_main_category_views.xml',
        'views/estate_lease_contract_rental_turnover_percentage_views.xml',
        'views/estate_lease_contract_rental_period_percentage_views.xml',
        'views/estate_lease_contract_property_management_fee_plan_views.xml',
        'views/estate_lease_contract_rental_plan_views.xml',
        'views/estate_lease_contract_rental_plan_rel_views.xml',
        'views/estate_lease_contract_registration_addr_rel_views.xml',
        'views/estate_lease_contract_views.xml',
        'views/estate_lease_contract_property_daily_status_views.xml',
        'views/estate_lease_contract_menus.xml',

        'data/cron_daily_property_status.xml',

        'report/estate_lease_contract_rent_payment_notice_reports.xml',
        'report/estate_lease_contract_rent_payment_notice_templates.xml',
    ],
    'license': 'AGPL-3'
}
