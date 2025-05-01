# -*- coding: utf-8 -*-
{
    'name': "资产管理大屏",

    'summary': """
        呈现资产租赁指标
    """,

    'description': """
        全面展示资产出租率、出租价格走势等信息
    """,

    'author': "北京491科技",
    'website': "http://www.491tech.com/",
    'category': 'Real Estate/Estate Big Screen',
    'version': '0.1',
    'application': True,
    'installable': True,
    'depends': ['base', 'web', 'estate', 'estate_lease_contract'],

    'data': [
        'security/security.xml',
        'views/estate_big_screen_views.xml',
        'views/estate_big_screen_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'estate_big_screen/static/src/**/*',
        ],
    },
    'license': 'AGPL-3'
}
