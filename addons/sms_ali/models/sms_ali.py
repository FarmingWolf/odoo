# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os
import shutil
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from addons.estate_dashboard.services.service import EstateDashboardService
from odoo import models, fields, api
from odoo.tools import date_utils, config
from odoo.tools.safe_eval import dateutil

_logger = logging.getLogger(__name__)


def _compute_date_send(self, rule):
    date_send = fields.Datetime.context_timestamp(self, fields.datetime.now()).replace(tzinfo=None)

    if rule.sms_send_period == "daily":
        pass
    elif rule.sms_send_period == "weekly":
        weekday = date_send.weekday() + 1
        date_send = date_send + timedelta(days=(int(rule.sms_send_period_weekday) - weekday + 7) % 7)

    elif rule.sms_send_period == "monthly":
        monthday = date_send.day
        if monthday <= rule.sms_send_period_monthday:
            date_send = date_send + relativedelta(day=rule.sms_send_period_monthday)
        else:
            date_send = date_send + relativedelta(months=1, day=rule.sms_send_period_monthday)
    elif rule.sms_send_period == "depends_on":
        pass
    else:
        _logger.error("目前没有这种情况")
        pass

    date_send = date_send.replace(hour=rule.sms_send_time_h, minute=rule.sms_send_time_m, second=0, microsecond=0)
    _logger.info(f"date_send={date_send}")
    return date_send


def _need_create_sms_rcd(self, rule):
    rcd_send_date = _compute_date_send(self, rule)
    if not rule.latest_sent_time:
        return True, rcd_send_date
    else:
        _logger.info(f"latest_sent_time={rule.latest_sent_time}"
                     f"{'<' if rule.latest_sent_time < rcd_send_date else '>='}"
                     f"{rcd_send_date}")
        if rule.latest_sent_time < rcd_send_date:
            _logger.info(f"rcd_send_date.date={rcd_send_date.date()}"
                         f"{'==' if rcd_send_date.date() == fields.Date.context_today(self) else '!='}"
                         f"fields.Date.context_today(self)={fields.Date.context_today(self)}")
            if rcd_send_date.date() == fields.Date.context_today(self):
                return True, rcd_send_date
            else:
                return False, rcd_send_date
        else:
            return False, rcd_send_date


def _set_template_property_rent_ratio_common(json_data):
    hist_sent_content_params = {
        "park_n": json_data['company_name'],
        "p_cnt": json_data['estate_property_quantity'],
        "area_cnt": round(json_data['estate_property_area_quantity'], 2),
        "on_rent_p": json_data['estate_property_lease_quantity'],
        "ratio_p": round(json_data['ratio_property_quantity'] * 100, 2),
        "on_rent_area": round(json_data['estate_property_area_lease_quantity'], 2),
        "ratio_area": round(json_data['ratio_property_area_quantity'] * 100, 2),
    }
    hist_text_content = f"截至今日{json_data['company_name']}" \
                        f"总房间数{json_data['estate_property_quantity']}，" \
                        f"总面积{round(json_data['estate_property_area_quantity'], 2)}㎡，" \
                        f"在租房间数{json_data['estate_property_lease_quantity']}" \
                        f"占比{round(json_data['ratio_property_quantity'] * 100, 2)}%，" \
                        f"在租面积{round(json_data['estate_property_area_lease_quantity'], 2)}㎡" \
                        f"占比{round(json_data['ratio_property_area_quantity'] * 100, 2)}%。"
    return hist_sent_content_params, hist_text_content


def _set_template_property_rent_ratio_491(json_data):
    room_cnt = 0
    area_cnt = 0
    not_rent = 0
    not_rent_area = 0
    woods_pieces = 0
    woods_area = 0
    woods_not_rent_pieces = 0
    woods_not_rent_area = 0

    for record in json_data['latest_property_detail']:
        if (not record.property_id.property_type_id) or record.property_id.property_type_id.count_ratio_as_room:
            room_cnt += 1
            area_cnt += record.property_rent_area
            if (not record.property_state) or record.property_state not in ('sold', '已租'):
                not_rent += 1
                not_rent_area += record.property_rent_area

        else:
            woods_pieces += 1
            woods_area += record.property_rent_area
            if (not record.property_state) or record.property_state not in ('sold', '已租'):
                woods_not_rent_pieces += 1
                woods_not_rent_area += record.property_rent_area

    wood_info = "无空置" if woods_not_rent_pieces == 0 else f"空置{woods_not_rent_pieces}块，空置面积{woods_not_rent_area}㎡"

    ratio_out_area = not_rent_area / area_cnt if area_cnt != 0 else 0

    hist_sent_content_params = {
        "room_cnt": room_cnt,
        "area_cnt": round(area_cnt, 2),
        "not_rent": not_rent,
        "not_rent_area": round(not_rent_area, 2),
        "ratio_out_area": round(ratio_out_area * 100, 2),
        "woods_pieces": woods_pieces,
        "woods_area": round(woods_area, 2),
        "wood_info": wood_info,
    }

    hist_text_content = f"截至今日491空间房间总数{room_cnt}，总面积{round(area_cnt, 2)}㎡，空置{not_rent}间，" \
                        f"空置面积{round(not_rent_area, 2)}㎡，空置率{round(ratio_out_area * 100, 2)}%；" \
                        f"此外，林地{woods_pieces}块，面积{round(woods_area, 2)}㎡，{wood_info}。"
    return hist_sent_content_params, hist_text_content


class SmsAli(models.Model):
    _name = 'sms.ali'
    _description = 'SMS sending by aliyun'
    _order = 'tgt_partner_id ASC'

    tgt_partner_id = fields.Many2one(string="短信对象", comodel_name="res.partner")
    tgt_mobile = fields.Char(string="手机号", related="tgt_partner_id.mobile", readonly=True)
    sms_sign_name = fields.Char(string="短信签名", help="来自阿里云短信服务的签名SmsSign，必须保持一致")
    sms_template_name = fields.Char(string="模板名称", help="来自阿里云短信服务的TemplateName，必须保持一致")
    sms_template_code = fields.Char(string="模板编码", help="来自阿里云短信服务的TemplateCode，必须保持一致")
    sms_template_content = fields.Text(string="模板内容", help="来自阿里云短信服务的TemplateContent，内容必须保持一致")
    sms_template_params = fields.Text(string="模板参数", help="来自阿里云短信服务的TemplateParams，格式必须保持一致")
    sms_send_period = fields.Selection(string="发送周期", default="daily",
                                       selection=[('daily', '每天'), ('weekly', '每周'), ('monthly', '每月'),
                                                  ('depends_on', '按实际合同情况')], )
    sms_send_period_weekday = fields.Selection(string="每周", default='1',
                                               selection=[('1', '一'), ('2', '二'), ('3', '三'), ('4', '四'), ('5', '五'),
                                                          ('6', '六'), ('7', '日')])
    sms_send_period_monthday = fields.Integer(string="每月", default=1)
    sms_send_time_h = fields.Integer(string="发送时间", default=10, help="23：00~7：00之间不允许发短信（运营商拦截）")
    sms_send_time_m = fields.Integer(string="发送时间（分）", default=0)
    sms_send_time_hhmm = fields.Char(string="发送时间(时分)", compute="_get_sms_send_time_hhmm", readonly=True)
    sms_send_period_descript = fields.Char(string="周期描述", compute="_get_sms_send_period_descript", readonly=True)
    latest_sent_time = fields.Datetime(string="最近发送时间", readonly=True, copy=False)  # 由短信发送程序更新回写
    active = fields.Boolean(string="有效", default=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends("sms_send_period", "sms_send_period_weekday", "sms_send_period_monthday", "sms_send_time_h",
                 "sms_send_time_m")
    def _get_sms_send_period_descript(self):
        for record in self:
            temp_str = dict(record._fields['sms_send_period'].selection).get(record.sms_send_period)
            if record.sms_send_period == "daily":
                record.sms_send_period_descript = temp_str + record.sms_send_time_hhmm
            if record.sms_send_period == "weekly":
                record.sms_send_period_descript = temp_str + dict(record._fields['sms_send_period_weekday'].
                                                                  selection).get(record.sms_send_period_weekday) + \
                                                  record.sms_send_time_hhmm
            if record.sms_send_period == "monthly":
                record.sms_send_period_descript = temp_str + str(record.sms_send_period_monthday) + "号" + \
                                                  record.sms_send_time_hhmm
            if record.sms_send_period == "depends_on":
                record.sms_send_period_descript = temp_str + "（租金支付日）" + record.sms_send_time_hhmm

    @api.depends("sms_send_time_h", "sms_send_time_m")
    def _get_sms_send_time_hhmm(self):
        for record in self:
            record.sms_send_time_hhmm = str(record.sms_send_time_h).zfill(2) + ":" + \
                                        str(record.sms_send_time_m).zfill(2)

    @api.onchange("sms_send_period_monthday")
    def _onchange_sms_send_period_monthday(self):
        if not self.sms_send_period_monthday or self.sms_send_period_monthday < 1:
            self.sms_send_period_monthday = 1
        if self.sms_send_period_monthday > 31:
            self.sms_send_period_monthday = 31

    @api.onchange("sms_send_time_h")
    def _onchange_sms_send_time_h(self):
        if not self.sms_send_time_h or self.sms_send_time_h < 7:
            self.sms_send_time_h = 7
        if self.sms_send_time_h > 22:
            self.sms_send_time_h = 22

    @api.onchange("sms_send_time_m")
    def _onchange_sms_send_time_m(self):
        if not self.sms_send_time_m or self.sms_send_time_m < 0:
            self.sms_send_time_m = 0
        if self.sms_send_time_m > 59:
            self.sms_send_time_m = 59

    def create_sms_rcd_by_rules(self):
        sms_rules = self.env['sms.ali'].sudo().search([('active', '=', True)], order="company_id, tgt_partner_id")
        for rule in sms_rules:
            # 先看本条是否要做成短信数据
            need_create, send_date = _need_create_sms_rcd(self, rule)
            if not need_create:
                _logger.info(f"【跳过】id={rule.id},发送周期：{rule.sms_send_period_descript},send_date={send_date}")
                continue

            res = self.env['sms.ali.hist'].sudo().search([('sms_ali_id', '=', rule.id), ('date_send', '=', send_date)])
            if res:
                _logger.info(f"【跳过】id={rule.id},mobile={rule.tgt_mobile}，{rule.sms_template_name}"
                             f"发送周期：{rule.sms_send_period_descript},发送时间：{send_date}已存在")
                continue

            hist_sms_ali_id = rule.id
            hist_tgt_partner_id = rule.tgt_partner_id
            hist_tgt_mobile = rule.tgt_mobile
            hist_sms_sign_name = rule.sms_sign_name
            hist_sms_template_name = rule.sms_template_name
            hist_sms_template_code = rule.sms_template_code
            hist_company_id = rule.company_id.id
            hist_date_send = send_date
            if "资产出租率汇报" in rule.sms_template_name:
                json_data = EstateDashboardService.get_statistics_svc(company_id=rule.company_id.id,
                                                                      env=self.env(su=True))
                if '491' in rule.sms_template_name:
                    hist_sent_content_params, hist_text_content = _set_template_property_rent_ratio_491(json_data)
                else:
                    json_data["company_name"] = rule.company_id.name
                    hist_sent_content_params, hist_text_content = _set_template_property_rent_ratio_common(json_data)

            # 写入hist
            self.env['sms.ali.hist'].sudo().create({
                "sms_ali_id": hist_sms_ali_id,
                "tgt_partner_id": hist_tgt_partner_id,
                "tgt_mobile": hist_tgt_mobile,
                "sms_sign_name": hist_sms_sign_name,
                "sms_template_name": hist_sms_template_name,
                "sms_template_code": hist_sms_template_code,
                "date_send": hist_date_send,
                "date_sent": None,
                "sent_result": None,
                "sent_content_params": str(hist_sent_content_params),
                "text_content": hist_text_content,
                "company_id": hist_company_id,
            })

    @staticmethod
    def log_rotate() -> None:
        today_str = datetime.today().strftime("%Y%m%d")
        rotate_days = config.get('logrotate_days', '365')
        log_file_path = config.get('logfile')

        if os.path.exists(log_file_path):
            if not os.path.exists(log_file_path + today_str):
                shutil.copy(log_file_path, log_file_path + today_str)
                open(log_file_path, 'w').close()
            else:
                print(f"{log_file_path + today_str} not exists")

        for i in range(30):
            del_tgt = (datetime.today() - relativedelta(days=int(rotate_days) + i)).strftime("%Y%m%d")
            del_tgt = log_file_path + del_tgt
            if os.path.exists(del_tgt):
                print(f"delete {del_tgt}")
                os.remove(del_tgt)
