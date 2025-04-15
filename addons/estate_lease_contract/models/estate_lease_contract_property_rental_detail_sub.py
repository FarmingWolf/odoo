# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta, date
from odoo import fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EstateLeaseContractPropertyRentalDetailSub(models.Model):
    _name = "estate.lease.contract.property.rental.detail.sub"
    _description = "资产租赁合同租金明细子批次"
    _order = "date_received"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="租金分次缴费详情", default="租金分次缴费详情")
    rental_detail_id = fields.Many2one('estate.lease.contract.property.rental.detail', string="租金明细ID",
                                       ondelete="cascade", readonly=True)

    rental_receivable_this = fields.Float(default=0.0, string="本次应收(元)", compute="_compute_received",
                                          store=True, compute_sudo=True)
    rental_received = fields.Float(default=0.0, string="本次实收(元)", tracking=True)

    date_received = fields.Date(string="实收日期", default=lambda self: fields.Date.context_today(self), tracking=True)
    rental_received_sum = fields.Float(default=0.0, string="累计实收(元)", readonly=True, compute="_compute_received",
                                       store=True, compute_sudo=True)
    days_received = fields.Float(string="实收天数", readonly=True, store=True, compute="_compute_received",
                                 compute_sudo=True)
    days_received_sum = fields.Float(string="累计实收天数", readonly=True, store=True, compute="_compute_received",
                                     compute_sudo=True)
    rental_arrears = fields.Float(string="欠缴金额", readonly=True, store=True, compute="_compute_received",
                                  compute_sudo=True)
    days_arrears = fields.Float(string="欠缴天数", readonly=True, store=True, compute="_compute_received",
                                compute_sudo=True)
    rental_received_2_date = fields.Date(string="实收至", readonly=True, store=True, compute="_compute_received",
                                         compute_sudo=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True,
                                 ondelete="cascade")

    # 以下字段要在页面显示
    property_id = fields.Many2one('estate.property', related="rental_detail_id.property_id", string="资产",
                                  ondelete="cascade")
    contract_id = fields.Many2one('estate.lease.contract', related="rental_detail_id.contract_id", string="合同",
                                  ondelete="cascade")
    contract_state = fields.Selection(related="contract_id.state", string="合同状态")
    party_a_unit_id = fields.Many2one("estate.lease.contract.party.a.unit", related="contract_id.party_a_unit_id",
                                      ondelete="set null")
    party_a_unit_invisible = fields.Boolean(string="甲方显示与否", related="contract_id.party_a_unit_invisible")
    date_start = fields.Date(string="合同开始日期", related="contract_id.date_start")
    date_rent_start = fields.Date(string="计租开始日期", related="contract_id.date_rent_start")
    date_rent_end = fields.Date(string="计租结束日期", related="contract_id.date_rent_end")
    renter_id = fields.Many2one('res.partner', string="承租人", related='contract_id.renter_id', store=True,
                                ondelete="set null")
    contract_amount = fields.Float(string="合同总额（元）", related='contract_id.contract_amount')
    rental_receivable_tgt_period = fields.Float(string="指定期间应收（元）", related='rental_detail_id.rental_receivable')
    rental_received_tgt_period = fields.Float(string="指定期间实收（元）", related='rental_detail_id.rental_received')
    rental_arrears_tgt_period = fields.Float(string="指定期间欠缴（元）", related='rental_detail_id.rental_arrears')
    period_date_from = fields.Date(string="本期开始日", related="rental_detail_id.period_date_from")
    period_date_to = fields.Date(string="本期结束日", related="rental_detail_id.period_date_to")
    date_payment = fields.Date(string="本期约定支付日", related="rental_detail_id.date_payment")
    rental_period_no = fields.Integer(string="本期期数", related="rental_detail_id.rental_period_no")
    active = fields.Boolean(related="rental_detail_id.active", store=True)
    receipt_status = fields.Selection(string="发票状态", selection=[('applied', '已申请，未开票'), ('done', '已开票')],
                                      default=None, tracking=True, compute="_compute_receipt_status", store=True)
    receipt_type = fields.Selection(string="发票类型", selection=[('zp', '专票'), ('pp', '普票')],
                                    default=None, tracking=True, store=True)
    receipt_type_editable = fields.Boolean(string="发票类型可编辑",
                                           compute="_compute_receipt_type_editable")
    receipt_apply_uid = fields.Many2one(string="发票申请人", comodel_name="res.users", tracking=True)
    receipt_apply_date = fields.Date(string="发票申请时间", tracking=True)
    rental_receipt = fields.Boolean(string="发票", tracking=True)
    rental_receipt_evidence = fields.Html(string="发票信息", store=True)
    rental_receipt_editable = fields.Boolean(string="发票信息可编辑",
                                             compute="_compute_rental_receipt_editable")
    receipt_done_by_uid = fields.Many2one(string="发票开具人", comodel_name="res.users", tracking=True)
    receipt_done_date = fields.Date(string="发票开具时间", tracking=True)

    def _compute_rental_receipt_editable(self):
        for record in self:
            record.rental_receipt_editable = \
                self.env.user.has_group('estate_lease_contract.contract_brokerage_invoice_manage')

    def _compute_receipt_type_editable(self):
        is_editable = self.env.user.has_group('estate.estate_group_business')
        for record in self:
            if not is_editable:
                record.receipt_type_editable = False
            else:
                if record.rental_receipt:
                    record.receipt_type_editable = False
                else:
                    record.receipt_type_editable = True

    @api.depends("rental_received", "date_received")
    def _compute_received(self):
        for record in self:
            self._compute_by_received(record)

    @api.onchange("rental_received", "date_received")
    def _onchange_rental_received(self):
        records = self.browse(self.env.context.get('active_ids', [])) | self
        records = records.sorted(key=lambda r: r.date_received)

        received_sum = 0
        for record in records:
            received_sum += record.rental_received
            if record.rental_received_sum != received_sum:
                record.rental_received_sum = received_sum

    def automatic_cal_by_received(self):
        rcds = self.env["estate.lease.contract.property.rental.detail.sub"].sudo().search([('active', '=', True)],
                                                                                          order="date_received ASC")
        for rcd in rcds:
            self._compute_by_received(rcd)

    def _compute_by_received(self, in_rcd):
        _logger.debug(f"开始计算company_id={in_rcd.company_id},detail_sub_id={in_rcd.id}")
        domain = [('rental_detail_id', '=', in_rcd.rental_detail_id.id), ('active', '=', True)]
        rcds = self.env["estate.lease.contract.property.rental.detail.sub"].sudo().search(domain)
        received_sum = 0.0
        days_cal_sum = 0.0
        received_sum_this_time = 0.0
        days_cal_this_time = 0.0
        days_cal_sum_this_time = 0.0

        for rcd in rcds:
            received_sum += rcd.rental_received
            if rcd.rental_received_sum != received_sum:
                rcd.rental_received_sum = received_sum

            if in_rcd.rental_detail_id.rental_receivable:
                days_cal = rcd.rental_received / in_rcd.rental_detail_id.rental_receivable * \
                           in_rcd.rental_detail_id.days_receivable
                days_cal_sum += days_cal
                if rcd.days_received != days_cal:
                    rcd.days_received = days_cal

                if rcd.days_received_sum != days_cal_sum:
                    rcd.days_received_sum = days_cal_sum

                if rcd.rental_arrears != in_rcd.rental_detail_id.rental_receivable - rcd.rental_received_sum:
                    rcd.rental_arrears = in_rcd.rental_detail_id.rental_receivable - rcd.rental_received_sum

                # 根据本次实收和欠缴反算本次应收（不同于总应收）
                if rcd.rental_receivable_this != rcd.rental_received + rcd.rental_arrears:
                    rcd.rental_receivable_this = rcd.rental_received + rcd.rental_arrears

                if rcd.days_arrears != in_rcd.rental_detail_id.days_receivable - rcd.days_received_sum:
                    rcd.days_arrears = in_rcd.rental_detail_id.days_receivable - rcd.days_received_sum

                date_2 = in_rcd.rental_detail_id.period_date_from + timedelta(days=rcd.days_received_sum - 1)
                if rcd.rental_received_2_date != date_2:
                    rcd.rental_received_2_date = date_2

                if rcd.date_received <= in_rcd.date_received:
                    received_sum_this_time = received_sum
                    days_cal_this_time = days_cal
                    days_cal_sum_this_time = days_cal_sum

        if in_rcd.rental_received_sum != received_sum_this_time:
            in_rcd.rental_received_sum = received_sum_this_time

        if in_rcd.days_received != days_cal_this_time:
            in_rcd.days_received = days_cal_this_time

        if in_rcd.days_received_sum != days_cal_sum_this_time:
            in_rcd.days_received_sum = days_cal_sum_this_time

        if in_rcd.rental_arrears != in_rcd.rental_detail_id.rental_receivable - in_rcd.rental_received_sum:
            in_rcd.rental_arrears = in_rcd.rental_detail_id.rental_receivable - in_rcd.rental_received_sum

        if in_rcd.days_arrears != in_rcd.rental_detail_id.days_receivable - in_rcd.days_received_sum:
            in_rcd.days_arrears = in_rcd.rental_detail_id.days_receivable - in_rcd.days_received_sum

        # 计算本次应收（不同于总应收）
        if in_rcd.rental_receivable_this != in_rcd.rental_received + in_rcd.rental_arrears:
            in_rcd.rental_receivable_this = in_rcd.rental_received + in_rcd.rental_arrears

        date_2_this_time = in_rcd.rental_detail_id.period_date_from + timedelta(days=in_rcd.days_received_sum - 1)
        if in_rcd.rental_received_2_date != date_2_this_time:
            in_rcd.rental_received_2_date = date_2_this_time

    def action_apply_rental_invoice(self):
        for record in self:
            if record.rental_received < 0.01:
                raise UserError("开票金额有误！")
            if record.receipt_status != 'applied':
                record.receipt_status = 'applied'
                record.receipt_apply_uid = self.env.user.id
                record.receipt_apply_date = date.today()
                record._set_default_rental_receipt_evidence()

            if not record.receipt_type:
                record.receipt_type = 'zp'

    @api.onchange("rental_receipt")
    def _onchange_rental_receipt(self):
        if self.rental_receipt:
            self.receipt_done_by_uid = self.env.user.id
            self.receipt_done_date = date.today()
            self._set_default_rental_receipt_evidence()


    @api.depends("rental_receipt", "rental_receipt_evidence")
    def _compute_receipt_status(self):
        for record in self:
            if record.rental_receipt and record.rental_receipt_evidence:
                if record.receipt_status != 'done':
                    record.receipt_status = 'done'
                    record.receipt_done_by_uid = self.env.user.id
                    record.receipt_done_date = date.today()
            else:
                if record.receipt_status == 'done':
                    record.receipt_status = 'applied'

    def _set_default_rental_receipt_evidence(self):
        if not self.rental_receipt_evidence:
            tmp_str = []
            if self.renter_id:
                if self.renter_id.is_company:
                    tmp_str.append(f"企业统一信用代码:{str(self.renter_id.vat)}")
                    tmp_str.append(f"开票名称：{str(self.renter_id.name)}")
                else:
                    tmp_str.append(f"开票对象：个人")
                    tmp_str.append(f"开票名称：{str(self.renter_id.name)}")

            if self.receipt_apply_uid:
                tmp_str.append(f"申请人：{self.receipt_apply_uid.name}")
                tmp_str.append(f"申请时间：{self.receipt_apply_date}")

            self.rental_receipt_evidence = tmp_str
