# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime

from dateutil.utils import today

from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class EstateLeaseContractBankAccount(models.Model):

    _name = "estate.lease.contract.bank.account"
    _description = "资产租赁合同收款账户模型"

    name = fields.Char('资产租赁银行账户', required=True, translate=True)

    bank_id = fields.Char('银行ID', required=True, translate=True)
    bank_name = fields.Char('银行名称', required=True, translate=True)
    bank_branch_id = fields.Char('银行支行ID', required=True, translate=True)
    bank_branch_name = fields.Char('银行支行名称', required=True, translate=True)
    bank_branch_addr = fields.Char('银行支行地址', required=True, translate=True)

    bank_account_id = fields.Char('银行账户号', required=True, translate=True)
    bank_account_name = fields.Char('银行账户名称', required=True, translate=True)
