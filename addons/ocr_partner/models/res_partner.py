# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo import api, fields, models
import pytesseract
from PIL import Image
import io
import base64
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    file_upload = fields.Binary(string="Image", help="为提高识别度，请上传清晰图片，不要有水印。同时，文件大小控制在5M以内。")
    file_preview = fields.Html(string="图片预览", readonly=True)
    extracted_text = fields.Text(string="Extracted Text", readonly=True, store=False)

    def _compute_file_preview(self, file_bytes=None):
        for record in self:
            if file_bytes:
                # 确保 file_upload 是字符串，而不是字节字符串
                file_upload_str = record.file_upload.decode('utf-8') if isinstance(file_bytes,
                                                                                   bytes) else file_bytes
                # 移除可能的换行符或空格
                file_upload_str = file_upload_str.strip()
                record.file_preview = f'<img src="data:image/png;base64,{file_upload_str}" style="max-width: 300px;"/>'
            else:
                record.file_preview = False

    def extract_business_info(self, text):
        for record in self:
            # 正则表达式匹配字段
            patterns = {
                'name': r'名\s*称\s*([\u4e00-\u9fa5]+.*?)(?=   注)',
                'street2': r'住\s*所\s*([^\n]+)',
                'vat': r'([A-Z0-9]{18})',
                'registered_capital': r'注\s*册\s*资\s*本\s*([^\n]+)',
            }

            # 提取字段
            for field, pattern in patterns.items():
                match = re.search(pattern, text)
                if match:
                    if field == 'name':
                        record[field] = match.group(1).replace('名', '', 1).replace('称', '', 1).strip()
                    if field == 'street2':
                        record[field] = match.group(1).replace('住', '', 1).replace('所', '', 1).strip()
                        city_name_pattern = r'(.+?市)(.*)'
                        city_match = re.search(city_name_pattern, record[field])

                        if city_match:
                            record.city = city_match.group(1)
                            record.street = city_match.group(2)

                    if field == 'vat':
                        record[field] = match.group(1).strip()
                    if field == 'registered_capital':
                        capital_text = match.group(1)
                        record[field] = re.sub(r'[^\d.]', '', capital_text)

    def extract_text_from_file(self):
        for record in self:
            # 获取上传的文件
            file_data = record.file_upload
            if not file_data:
                record.file_preview = False
                return

            # 将Base64文件数据解码为字节
            file_bytes = base64.b64decode(file_data)

            # 使用Pillow打开图像文件
            image = Image.open(io.BytesIO(file_bytes))
            # 检测文字方向
            osd = pytesseract.image_to_osd(image)
            angle = int(re.search(r'Orientation in degrees: (\d+)', osd).group(1))

            # 根据角度旋转图片
            if angle == 90:
                image = image.rotate(-90, expand=True)  # 逆时针旋转90度
            elif angle == 180:
                image = image.rotate(-180, expand=True)  # 逆时针旋转180度
            elif angle == 270:
                image = image.rotate(-270, expand=True)  # 逆时针旋转270度
            # else:
            #     if image.height > image.width:
            #         image = image.rotate(-90, expand=True)

            # 调用Tesseract OCR进行文字识别
            custom_config = r'--oem 3 --psm 6 -l chi_sim'  # 使用简体中文语言包
            text = pytesseract.image_to_string(image, config=custom_config)

            # 将识别结果保存到字段中
            # record.extracted_text = text

            record.extract_business_info(text)
            record._compute_file_preview(file_bytes)
