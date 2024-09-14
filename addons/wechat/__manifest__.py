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
    'website': "https://www.491tech.com/",
    'category': 'Wechat/Wechat',
    'version': '0.1',
    'application': True,
    'installable': True,
    'depends': ['base', 'web'],

    'data': [
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'https://res.wx.qq.com/connect/zh_CN/htmledition/js/wxLogin.js',
            'wechat/static/src/js/wechat_login.js',
        ],
        'web.assets_backend': [
        ],
    },
    'license': 'AGPL-3'
}
