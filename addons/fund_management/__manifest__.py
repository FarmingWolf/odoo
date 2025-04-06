# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Fund Management',
    'version': '1.0',
    'category': 'Fund Management/Fund Approval',
    'sequence': 77,
    'summary': '工程类项目资金、服务类项目资金管理，创建和提交资金流程、资金流程审批。',
    'description': """
资金审批流程按金额分三档，默认分5万以下，5-30万，30万以上三档，可在应用设置页面自由配置；
审批流批准和拒绝，原则上逐级递进或退回；
可设置中间流程是否允许上传附件；
最高领导层增加一键叫停：流程直接打回至初始状态；
    """,
    'website': 'https://www.491tech.com/',
    'depends': ['account', 'web_tour', 'hr'],
    'data': [
        'security/fund_management_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'security/ir.rule.csv',
        'views/fund_management_meeting_minutes_type_views.xml',
        'views/fund_management_approval_detail_views.xml',
        'views/fund_management_approval_stage_views.xml',
        'views/fund_management_category_views.xml',
        'views/fund_management_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'fund_management/static/src/components/*.js',
            'fund_management/static/src/components/*.xml',
            'fund_management/static/src/mixins/*.js',
            'fund_management/static/src/views/*.js',
            'fund_management/static/src/views/*.xml',
            'fund_management/static/src/scss/fund_management.scss',
        ],
        'web.assets_tests': [
        ],
        'web.report_assets_common': [
            'fund_management/static/src/scss/fund_management.scss',
        ],
        'web.qunit_suite_tests': [
        ],
        'web.qunit_mobile_suite_tests': [
        ],
    },
    'license': 'LGPL-3',
}
