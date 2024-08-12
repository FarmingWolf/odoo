# -*- coding: utf-8 -*-
{
    'name': "微信",

    'summary': """
        对接微信
    """,

    'description': """
        对接微信，握手校验
    """,

    'author': "北京491科技",
    'website': "https://www.odoo.com/",
    'category': 'Wechat/Wechat',
    'version': '0.1',
    'application': True,
    'installable': True,
    'depends': ['base'],

    'data': [

    ],
    'assets': {
        'web.assets_backend': [
            'wechat/static/src/**/*',
        ],
    },
    'license': 'AGPL-3'
}
