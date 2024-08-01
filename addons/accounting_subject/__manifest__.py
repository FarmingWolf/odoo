# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "会计科目",
    'version': '0.1',
    'depends': ['base'],
    'category': 'Accounting/Accounting Subject',
    'summary': '会计科目，科目层级自由设置',
    'author': '491Tech',
    'website': 'https://www.odoo.com/',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'views/accounting_subject_views.xml',
    ],
    'assets': {
    },
    'license': 'AGPL-3'
}
