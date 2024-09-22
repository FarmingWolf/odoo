# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from alibabacloud_tea_util.client import Client as UtilClient

from odoo.tools import json

_logger = logging.getLogger(__name__)


def is_in_time(self, rcd):
    sys_time = fields.Datetime.context_timestamp(self, fields.datetime.now())
    if (sys_time - relativedelta(minutes=10)).strftime("%Y%m%d%H%M%S") <= rcd.date_send.strftime("%Y%m%d%H%M%S") <= \
            (sys_time + relativedelta(minutes=10)).strftime("%Y%m%d%H%M%S"):
        return True
    else:
        _logger.info(f"跳过id{rcd.id},mobile{rcd.tgt_mobile},date_send={rcd.date_send}非当前{sys_time}前后10分钟之内")
        return False


def set_single_param(self, send_tgt):
    res = {}
    for tgt in send_tgt:
        if not is_in_time(self, tgt):
            continue

        res = {
            "id": tgt.id,
            "phone_numbers": tgt.tgt_mobile,
            "sign_name": tgt.sms_sign_name,
            "template_code": tgt.sms_template_code,
            "template_param": tgt.sent_content_params,
        }
    return res


def set_batch_param(self, batch_param):
    phone_numbers = []
    sign_name = []
    template_param = []
    ids = []
    template_code = ""

    for record in batch_param:

        if not is_in_time(self, record):
            continue

        ids.append(record.id)
        phone_numbers.append(record.tgt_mobile)
        sign_name.append(record.sms_sign_name)
        template_param.append(record.sent_content_params)
        template_code = record.sms_template_code

    res = {
        "id": ids,
        "phone_numbers": phone_numbers,
        "sign_name": sign_name,
        "template_code": template_code,
        "template_param": template_param,
    }
    return res


@staticmethod
def create_client() -> Dysmsapi20170525Client:
    """
    使用AK&SK初始化账号Client
    @return: Client
    @throws Exception
    """
    # 工程代码泄露可能会导致 AccessKey 泄露，并威胁账号下所有资源的安全性。以下代码示例仅供参考。
    # 建议使用更安全的 STS 方式，更多鉴权访问方式请参见：https://help.aliyun.com/document_detail/378659.html。
    config = open_api_models.Config(
        # 必填，请确保代码运行环境设置了环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID。,
        access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
        # 必填，请确保代码运行环境设置了环境变量 ALIBABA_CLOUD_ACCESS_KEY_SECRET。,
        access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
    )
    # Endpoint 请参考 https://api.aliyun.com/product/Dysmsapi
    config.endpoint = f'dysmsapi.aliyuncs.com'
    return Dysmsapi20170525Client(config)


def send_sms_ali_batch(args: dict, process_type,):

    _logger.info(f"发送短信process_type={process_type}, args={args}")
    if not args or not args["id"]:
        _logger.info(f"没有要处理的短信")
        return args

    try:
        client = create_client()
        if process_type == "single":
            send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
                phone_numbers=args["phone_numbers"],
                sign_name=args["sign_name"],
                template_code=args["template_code"],
                template_param=args["template_param"],
            )
            _logger.info(f"single send_sms_request={send_sms_request}")
            send_resp = client.send_sms(send_sms_request)
        else:
            send_sms_request = dysmsapi_20170525_models.SendBatchSmsRequest(
                phone_number_json=json.dumps(args["phone_numbers"]),
                sign_name_json=json.dumps(args["sign_name"]),
                template_code=args["template_code"],
                template_param_json=json.dumps(args["template_param"]),
            )
            _logger.info(f"batch send_sms_request={send_sms_request}")
            send_resp = client.send_batch_sms(send_sms_request)

        bat_code = send_resp.body.code
        bat_err_msg = send_resp.body.message
        bat_biz_id = send_resp.body.biz_id
        args["err_code"] = bat_code
        args["err_msg"] = bat_err_msg
        args["biz_id"] = bat_biz_id

        # 走到这一步没出sys错误的话，就说明阿里云已经把sms发送给了运营商那边
        args["date_sent"] = fields.datetime.now()
        _logger.info(f'phone:{args["phone_numbers"]},发送【{args["template_param"]}】，bat_biz_id={bat_biz_id}，'
                     f'bat_code={bat_code}'
                     f'错误信息: {bat_err_msg}')

        if not UtilClient.equal_string(bat_code, 'OK'):
            _logger.error(f'phone:{args["phone_numbers"]},发送【{args["template_param"]}】，bat_biz_id={bat_biz_id}，'
                          f'bat_code={bat_code}'
                          f'错误信息: {bat_err_msg}')
            # 不着急返回return args

        # 2. 等待 10 秒后查询结果
        UtilClient.sleep(10 * 1000)
        # 3.查询结果
        phone_err_code = []
        phone_err_msg = []
        for phone_num in args["phone_numbers"]:
            query_req = dysmsapi_20170525_models.QuerySendDetailsRequest(
                phone_number=UtilClient.assert_as_string(phone_num),
                biz_id=bat_biz_id,
                send_date=fields.datetime.today().strftime('%Y%m%d'),
                page_size=10,
                current_page=1
            )
            query_resp = client.query_send_details(query_req)
            dtos = query_resp.body.sms_send_detail_dtos.sms_send_detail_dto
            _logger.info(f"SMS查询结果dtos={dtos}")
            # 打印结果
            for dto in dtos:

                phone_err_code.append(dto.err_code)

                if UtilClient.equal_string(f'{dto.send_status}', '3'):
                    this_phone_err_msg = f'{dto.phone_num} 发送成功，接收时间: {dto.receive_date}'
                elif UtilClient.equal_string(f'{dto.send_status}', '2'):
                    this_phone_err_msg = f'{dto.phone_num} 发送失败'
                else:
                    this_phone_err_msg = f'{dto.phone_num} 正在发送中...'

                _logger.info(this_phone_err_msg)
                phone_err_msg.append(this_phone_err_msg)

        args["phone_err_code"] = phone_err_code
        args["phone_err_msg"] = phone_err_msg
        args["process_type"] = process_type

        return args

    except Exception as error:
        # 此处仅做打印展示，请谨慎对待异常处理，在工程项目中切勿直接忽略异常。
        # 错误 message
        _logger.error(error)
        # 诊断地址
        _logger.error(error.data.get("Recommend"))
        UtilClient.assert_as_string(error)
        raise error


def set_bat_2_single_param(send_bat_param):
    res = {
        "id": send_bat_param["id"][0],
        "phone_numbers": send_bat_param["phone_numbers"][0],
        "sign_name": send_bat_param["sign_name"][0],
        "template_code": send_bat_param["template_code"],
        "template_param": send_bat_param["template_param"][0],
    }
    return res


class SmsAliHist(models.Model):
    _name = 'sms.ali.hist'
    _description = 'SMS sending history by aliyun'
    _order = 'id DESC'

    sms_ali_id = fields.Many2one(string="模板对象", comodel_name="sms.ali")

    tgt_partner_id = fields.Many2one(string="短信对象", comodel_name="res.partner", related="sms_ali_id.tgt_partner_id",
                                     readonly=True)
    tgt_mobile = fields.Char(string="手机号", related="sms_ali_id.tgt_mobile", readonly=True, store=True)
    sms_sign_name = fields.Char(string="短信签名", related="sms_ali_id.sms_sign_name", readonly=True)
    sms_template_name = fields.Char(string="模板名称", related="sms_ali_id.sms_template_name", readonly=True)
    sms_template_code = fields.Char(string="模板编码", related="sms_ali_id.sms_template_code", readonly=True, store=True)

    date_send = fields.Datetime(string="计划发送时间")
    date_send_no_tz = fields.Char(string="计划发送", compute="_get_date_send_no_tz", readonly=True)
    date_sent = fields.Datetime(string="实际发送时间")
    date_sent_no_tz = fields.Char(string="实际发送", compute="_get_date_sent_no_tz", readonly=True)
    sent_result = fields.Char(string="发送结果")
    sent_content_params = fields.Char(string="发送内容参数")
    text_content = fields.Char(string="短信完整内容")
    sms_size = fields.Char(string="长度")
    err_code = fields.Char(string="状态编码")
    err_msg = fields.Char(string="状态说明")
    biz_id = fields.Char(string="发送流水号")
    out_id = fields.Char(string="用户序列号")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.user.company_id, store=True)

    @api.depends("date_send")
    def _get_date_send_no_tz(self):
        for record in self:
            record.date_send_no_tz = str(record.date_send) if record.date_send else False

    @api.depends("date_sent")
    def _get_date_sent_no_tz(self):
        for record in self:
            record.date_sent_no_tz = str(record.date_sent) if record.date_sent else False

    def auto_get_send_tgt(self):
        send_tgt = self.env['sms.ali.hist'].sudo().search([('date_sent', '=', False)],
                                                          order="sms_template_code, tgt_mobile")
        _logger.info(f"send_tgt ids={send_tgt.ids}")
        if send_tgt:
            tgt_cnt = len(send_tgt)
            _logger.info(f"tgt_cnt={tgt_cnt}")
            if tgt_cnt == 1:
                send_tgt_param = set_single_param(self, send_tgt)
                ret_args = send_sms_ali_batch(send_tgt_param, "single")
                self.write_sent_result(ret_args)
            else:
                # 批量发送必须同一模板，每次最多100条
                i_s = 0
                i_e = 0
                for il in range(tgt_cnt):

                    # 最多100条
                    if il + 1 - i_s >= 100:
                        i_e = il + 1
                    else:
                        # 最后一条
                        if il == tgt_cnt - 1:
                            i_e = il + 1
                        else:
                            if send_tgt[il + 1].sms_template_code != send_tgt[il].sms_template_code \
                                    or send_tgt[il + 1].tgt_mobile == send_tgt[il].tgt_mobile:
                                i_e = il + 1

                    if i_e - i_s > 0:
                        _logger.info(f"准备整理发送对象{i_s}至{i_e}共{i_e - i_s}条")
                        send_bat_param = set_batch_param(self, send_tgt[i_s: i_e])
                        if send_bat_param and send_bat_param["id"] and len(send_bat_param["id"]) == 1:
                            send_bat_param = set_bat_2_single_param(send_bat_param)
                            ret_args = send_sms_ali_batch(send_bat_param, "single")
                        else:
                            ret_args = send_sms_ali_batch(send_bat_param, "batch")
                        i_s = i_e
                        self.write_sent_result(ret_args)

    def write_sent_result(self, args):
        if not args or not args["id"]:
            return

        ids = args["id"]
        phone_numbers = args["phone_numbers"]
        sign_name = args["sign_name"]
        template_code = args["template_code"]
        template_param = args["template_param"]
        process_type = args["process_type"]
        err_code = args["err_code"]
        err_msg = args["err_msg"]
        biz_id = args["biz_id"]
        date_sent = False
        if "date_sent" in args:
            date_sent = args["date_sent"]

        _logger.info(f"process_type={process_type}")
        if process_type == "batch":
            phone_err_code = args["phone_err_code"]
            phone_err_msg = args["phone_err_msg"]

        if isinstance(ids, int):
            send_tgt = self.env['sms.ali.hist'].sudo().search([('id', '=', ids)])
            send_tgt.biz_id = biz_id
            send_tgt.err_code = err_code
            send_tgt.err_msg = err_msg
            send_tgt.sent_result = err_code
            if date_sent:
                send_tgt.date_sent = date_sent
                send_tgt.sms_ali_id.latest_sent_time = date_sent

        else:
            i_cnt = len(ids)
            for i in range(i_cnt):
                send_tgt = self.env['sms.ali.hist'].sudo().search([('id', '=', ids[i])])
                send_tgt.biz_id = biz_id
                send_tgt.err_code = phone_err_code[i] if phone_err_code else False
                send_tgt.err_msg = phone_err_msg[i] if phone_err_msg else False
                send_tgt.sent_result = err_code
                if date_sent:
                    send_tgt.date_sent = date_sent
                    send_tgt.sms_ali_id.latest_sent_time = date_sent

    def receive_sms_report(self, bk_sms_report):
        for bk_data in bk_sms_report:
            biz_id = bk_data["biz_id"]
            tgt_mobile = bk_data["phone_number"]
            sent_date = bk_data["send_time"]
            result = bk_data["success"]
            err_code = bk_data["err_code"]
            err_msg = bk_data["err_msg"]
            sms_size = bk_data["sms_size"]
            # out_id = bk_data["out_id"]

            record = self.env['sms.ali.hist'].sudo().search([('tgt_mobile', '=', tgt_mobile), ('biz_id', '=', biz_id)])
            _logger.info(f"更新tgt_mobile{tgt_mobile},biz_id={biz_id},对象{len(record)}条")
            record.date_sent = sent_date
            record.sent_result = result
            record.err_code = err_code
            record.err_msg = err_msg
            record.sms_size = sms_size
            # record.out_id = out_id
            # 同时，也要把发送日期回写到模板的latest_sent_time
            for each_rcd in record:
                each_rcd.sms_ali_id.latest_sent_time = sent_date


