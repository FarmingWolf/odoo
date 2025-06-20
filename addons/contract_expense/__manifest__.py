# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': '支出类合同',
    'version': '1.0',
    'category': 'Contract/Expense',
    'sequence': 2,
    'summary': '支出类合同管理。',
    'description': """
    """,
    'website': 'https://zcgl.491tech.com/',
    'depends': ['base', 'account', 'hr', 'attachment_meeting_minutes', 'accounting_subject'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'security/ir.rule.csv',
        'views/contract_expense_fund_type_views.xml',
        'views/contract_expense_payment_method_views.xml',
        'views/contract_expense_procurement_method_views.xml',
        'views/contract_expense_category_views.xml',
        'views/contract_expense_approval_stage_views.xml',
        'views/contract_expense_views.xml',
        'views/contract_expense_menu_views.xml',

        'data/fund_type_data.xml',
        'data/payment_method_data.xml',
        'data/procurement_method_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'contract_expense/static/src/components/*.js',
            'contract_expense/static/src/components/*.xml',
        ],
        'web.assets_tests': [
        ],
        'web.report_assets_common': [
        ],
        'web.report_assets_pdf': [
        ],
        'web.qunit_suite_tests': [
        ],
        'web.qunit_mobile_suite_tests': [
        ],
    },
    'license': 'LGPL-3',
}
