# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "活动模型选项管理",
    'version': '2.1',
    'depends': ['base', 'event'],
    'category': 'Marketing/Event_Supervisor',
    'summary': '活动的扩展,管理活动选项，选项分组灵活应用于多种活动选项场景',
    'author': '491Tech',
    'website': 'https://www.odoo.com/',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/event_option_group_views.xml',
    ],
    'assets': {
    },
    'license': 'AGPL-3'
}
