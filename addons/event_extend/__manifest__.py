# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "活动模型扩展",
    'version': '2.1',
    'depends': ['event', 'website_event', 'website_event_track', 'event_option', 'operation_contract'],
    'category': 'Marketing/Event_Supervisor',
    'summary': '活动模块的扩展',
    'author': '491Tech',
    'website': 'https://www.odoo.com/',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'report/event_event_templates.xml',
        'report/event_event_reports.xml',
        'views/event_event_views.xml',
    ],
    'assets': {
        'web.report_assets_pdf': [
            '/event_extend/static/src/scss/event_extend.scss',
        ],
    },
    'license': 'AGPL-3'
}
