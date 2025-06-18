# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Attachment Meeting Minutes Management',
    'version': '1.0',
    'category': 'Attachment/Meeting Minutes',
    'sequence': 79,
    'summary': '会议纪要等附件管理。',
    'description': """
    """,
    'website': 'https://zcgl.491tech.com/',
    'depends': ['base', 'account', 'hr'],
    'data': [
        'security/attachment_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'security/ir.rule.csv',
        'views/meeting_minutes_type_views.xml',
        'views/meeting_minutes_views.xml',
        'views/meeting_minutes_menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'attachment_meeting_minutes/static/src/components/*.js',
            'attachment_meeting_minutes/static/src/components/*.xml',
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
