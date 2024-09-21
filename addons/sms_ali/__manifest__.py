# -*- coding: utf-8 -*-
{
    'name': 'SMS aliyun',
    'summary': 'SMS aliyun Text Messaging',
    'description': """This module gives a framework for SMS aliyun text messaging""",
    'author': "北京491科技",
    'website': "https://www.491tech.com/",
    'category': 'aliyun/Tools',
    'version': '1.5',
    'application': True,
    'installable': True,
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.csv',

        'views/sms_ali_hist_views.xml',
        'views/sms_ali_views.xml',
        'views/sms_ali_menus.xml',

        'data/cron_daily_sms_ali.xml',
    ],
    'assets': {
    },
    'license': 'AGPL-3',
}
