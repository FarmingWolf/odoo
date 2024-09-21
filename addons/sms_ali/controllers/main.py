# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
import logging
import os
import sys

from typing import List

from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.tools import json

_logger = logging.getLogger(__name__)


class SMSAliyun(http.Controller):
    # def __init__(self):
    #     pass

    @http.route('/sms-aliyun/sent-result', type='http', auth='public', methods=['POST'], csrf=False)
    def sms_ali_sent_result(self, bk_param=None):
        _logger.info(f"来自阿里云的SMSReport calling……bk_param={bk_param}")
        bk_data = request.httprequest.data
        # _logger.info(f"短信发送结果回调bk_data={bk_data}")
        bk_data_str = bk_data.decode('utf-8')
        _logger.info(f"短信发送结果回调bk_data_str={bk_data_str}")
        env = request.env(user=SUPERUSER_ID, su=True)
        sms_ali_hist = env['sms.ali.hist']
        sms_ali_hist.receive_sms_report(json.loads(bk_data_str))

        ret = {
            "code": 0,
            "msg": "接收成功",
        }
        return json.dumps(ret)

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

    @staticmethod
    def main(
            args: List[str],
    ) -> None:
        client = SMSAliyun.create_client()
        send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
            phone_numbers='18612801821',
            sign_name='四九一科技',
            template_code='SMS_473330261',
            template_param='{"park_n": "四九一园区", "p_cnt": "59", "area_cnt": "32975.79", "on_rent_p": "42",'
                           '"ratio_p": "71", "on_rent_area": "27810.66", "ratio_area": "84"}'
        )
        try:
            # 复制代码运行请自行打印 API 的返回值
            # client.send_sms_with_options(send_sms_request, util_models.RuntimeOptions())
            send_resp = client.send_sms(send_sms_request)
            code = send_resp.body.code
            if not UtilClient.equal_string(code, 'OK'):
                _logger.error(f'错误信息: {send_resp.body.message}')
                return
            biz_id = send_resp.body.biz_id
            # 2. 等待 10 秒后查询结果
            UtilClient.sleep(10000)
            # 3.查询结果
            phone_nums = '18611787912'
            for phone_num in phone_nums:
                query_req = dysmsapi_20170525_models.QuerySendDetailsRequest(
                    phone_number=UtilClient.assert_as_string(phone_num),
                    biz_id=biz_id,
                    send_date='20240919',
                    page_size=10,
                    current_page=1
                )
                query_resp = client.query_send_details(query_req)
                dtos = query_resp.body.sms_send_detail_dtos.sms_send_detail_dto
                # 打印结果
                for dto in dtos:
                    if UtilClient.equal_string(f'{dto.send_status}', '3'):
                        _logger.info(f'{dto.phone_num} 发送成功，接收时间: {dto.receive_date}')
                    elif UtilClient.equal_string(f'{dto.send_status}', '2'):
                        _logger.info(f'{dto.phone_num} 发送失败')
                    else:
                        _logger.info(f'{dto.phone_num} 正在发送中...')
        except Exception as error:
            # 此处仅做打印展示，请谨慎对待异常处理，在工程项目中切勿直接忽略异常。
            # 错误 message
            print(error.message)
            # 诊断地址
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)

    @staticmethod
    async def main_async(
            args: List[str],
    ) -> None:
        client = SMSAliyun.create_client()
        send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
            phone_numbers='18611787912',
            sign_name='四九一科技'
        )
        try:
            # 复制代码运行请自行打印 API 的返回值
            await client.send_sms_with_options_async(send_sms_request, util_models.RuntimeOptions())
        except Exception as error:
            # 此处仅做打印展示，请谨慎对待异常处理，在工程项目中切勿直接忽略异常。
            # 错误 message
            print(error.message)
            # 诊断地址
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)


# if __name__ == '__main__':
#     SMSAliyun.main(sys.argv[1:])
