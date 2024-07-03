# -*- coding: utf-8 -*-
{
    'name': "资产管理仪表盘",

    'summary': """
        资产租赁状态等指标
    """,

    'description': """
        全面展示资产租赁状态等指标
    """,

    'author': "北京491科技",
    'website': "https://www.odoo.com/",
    'category': 'Real Estate/Estate Dashboard',
    'version': '0.2',
    'application': True,
    'installable': True,
    'depends': ['base', 'web', 'estate', 'estate_lease_contract'],

    'data': [
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate_dashboard/static/src/**/*',
            ('remove', 'estate_dashboard/static/src/dashboard/**/*'),
        ],
        'estate_dashboard.dashboard': [
            'estate_dashboard/static/src/dashboard/**/*'
        ]
    },
    'license': 'AGPL-3'
}
