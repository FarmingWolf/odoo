# -*- coding: utf-8 -*-
{
    'name': '房源在线',
    'version': '0.4',
    'sequence': 186,
    'summary': '在线招商',
    'website': 'https://zcgl.491tech.com/estate_ads',
    'category': 'Website/estate',
    'description': "在线招商房源广告",
    'depends': [
        'web', 'portal_rating', 'website', 'website_mail', 'website_profile', 'estate',
    ],
    'data': [
        'security/website_estate_security.xml',
        'security/ir.model.access.csv',

        'views/estate_slide_property_views.xml',
        'views/estate_slide_property_menus.xml',
        'views/estate_slide_templates_homepage.xml',
        'views/estate_slide_templates_property_ad.xml',
    ],

    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/fontawesome_overridden.scss',
        ],
        'web.assets_frontend': [
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/src/legacy/js/public/public_widget',
            'website_estate/static/src/scss/website_property_slides.scss',
            'website_estate/static/src/js/property_ad.js',

        ],
        'website.assets_editor': [
        ],
    },
    'license': 'LGPL-3',
}
