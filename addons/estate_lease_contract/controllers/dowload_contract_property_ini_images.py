import base64
import logging

from odoo import http
from odoo.http import request, content_disposition
from io import BytesIO
import zipfile


_logger = logging.getLogger(__name__)


def _get_zip_headers(content, filename):
    return [
        ('Content-Type', 'zip'),
        ('X-Content-Type-Options', 'nosniff'),
        ('Content-Length', len(content)),
        ('Content-Disposition', content_disposition(filename)),
    ]


class DownloadContractPropertyIniImagesController(http.Controller):

    @http.route('/estate_lease_contract/download/all_images/<int:contract_id>', type='http', auth='user')
    def download_all_images(self, contract_id, **kwargs):

        contract = request.env['estate.lease.contract'].browse(contract_id)

        buffer = BytesIO()
        try:
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
                for record in contract.property_ini_img_ids:
                    if record.image_1920:
                        image_data = base64.b64decode(record.image_1920)
                        contract_nm = record.contract_id.name if record.contract_id else "-"
                        property_nm = record.property_id.name if record.property_id else "-"
                        write_time = record.write_date.strftime("%Y%m%d%H%M%S")
                        img_nm = contract_nm + "-" + property_nm + "-" + write_time + ".jpg"
                        if image_data:
                            info = zipfile.ZipInfo(img_nm)
                            zip_file.writestr(info, image_data)

            fn = f"all_images-{contract.name}-{contract.contract_no}.zip"
            _logger.info(f"下载zip文件名：{fn}")
            buffer.seek(0)
            zip_content = buffer.getvalue()
            _logger.info(f"content={zip_content[:100]}")
            headers = _get_zip_headers(zip_content, fn)

            _logger.info(f"headers={headers}")

            response = request.make_response(zip_content, headers)
            _logger.info(f"Response headers: {response.headers}")

            # 确保返回response
            return response
        except Exception as ex:
            _logger.info(f"exception：{ex}")
            _logger.error(f"error：{ex}")
            raise ex
        finally:
            _logger.info(f"finally try complete……")
