# fund_management/controllers/report_controller.py
import base64
import logging
import os
import sys

from ...web.controllers.home import Home
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class ReportController(Home):

    @http.route('/report/html/fund_management.contract_payment_application/<int:res_id>', type='http', auth='public')
    def contract_payment_application_report(self, res_id, **kw):
        _logger.info(f"打印有合同资金流程{res_id}")
        if sys.platform == "win32":
            report_name = "fund_management.contract_payment_application"
        else:
            report_name = "fund_management.contract_payment_application_linux"
        return self._render_report_html(report_name, res_id, **kw)

    @http.route('/report/html/fund_management.no_contract_payment_application/<int:res_id>', type='http', auth='public')
    def no_contract_payment_application_report(self, res_id, **kw):
        _logger.info(f"打印无合同资金流程{res_id}")
        if sys.platform == "win32":
            report_name = "fund_management.no_contract_payment_application"
        else:
            report_name = "fund_management.no_contract_payment_application_linux"

        return self._render_report_html(report_name, res_id, **kw)

    def _render_report_html(self, report_name, res_id, **kw):
        _logger.info(f"打印_render_html{res_id}")

        report = request.env['ir.actions.report'].sudo()._get_report(report_name)
        html = report._render_qweb_html(report_ref=report_name, docids=[res_id], data=kw)

        # font_base64_path = os.path.join(os.path.dirname(__file__), '../static/src/fonts/FZXBSJT_base64.txt')
        # with open(font_base64_path, 'r', encoding='utf-8') as f:
        #     base64_font = f.read()

        # html_new = html[0]
        # if isinstance(html_new, bytes):
        #     html_new = html_new.decode('utf-8')
        #     html_new = html_new.replace('font_base_64_bytes_of_fzxbsjt', base64_font)

        return request.make_response(html, headers=[('Content-Type', 'text/html')])
