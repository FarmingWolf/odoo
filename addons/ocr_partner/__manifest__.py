# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OCR Partner',
    'version': '1.0',
    'category': 'OCR/Partner',
    'summary': 'OCR Partner',
    'description': """
Using this application you can read business licence info through OCR.
=======================================================================
 """,
    'website': 'https://www.491tech.com/',
    'depends': ['base', 'mail', 'base_setup'],
    'data': [
        'views/res_partner_views.xml',
        ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
        ],
    },
    'license': 'LGPL-3',
}
