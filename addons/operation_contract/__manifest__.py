# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "运营合同管理",
    'depends': ['base', 'web', 'hr', 'event_option', 'website_event_track'],
    'summary': '运营活动合同审批等',
    'category': 'Operation/Operation Contract',
    'website': 'https://www.odoo.com/',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/operation_contract_approval_detail_views.xml',
        'views/operation_contract_stage_views.xml',
        'views/operation_contract_no_prefix_views.xml',
        'views/operation_contract_views.xml',
        'views/operation_contract_menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'operation_contract/static/src/scss/operation_contract.scss',
        ],
        'web.report_assets_pdf': [
            '/operation_contract/static/src/scss/operation_contract_report.scss',
        ],
    },
    'license': 'AGPL-3'
}
