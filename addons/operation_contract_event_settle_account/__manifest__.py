# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "合同活动结算",
    'version': '0.1',
    'depends': ['base', 'event_extend'],
    'category': 'Operation/Operation Contract',
    'summary': '根据活动开展实际情况结算合同',
    'author': '491Tech',
    'website': 'https://www.odoo.com/',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.csv',

        'views/operation_contract_event_settle_account_views.xml',
    ],
    'assets': {
    },
    'license': 'AGPL-3'
}
