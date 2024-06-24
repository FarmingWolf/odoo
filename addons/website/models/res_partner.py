# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import urllib

import requests
import werkzeug.urls

from odoo import models, fields, api

class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.published.multi.mixin']

    visitor_ids = fields.One2many('website.visitor', 'partner_id', string='Visitors')

    def google_map_img(self, zoom=8, width=298, height=298):
        google_maps_api_key = self.env['website'].get_current_website().google_maps_api_key
        if not google_maps_api_key:
            return False
        params = {
            'center': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.display_name or ''),
            'size': "%sx%s" % (width, height),
            'zoom': zoom,
            'sensor': 'false',
            'key': google_maps_api_key,
        }
        return '//maps.googleapis.com/maps/api/staticmap?' + werkzeug.urls.url_encode(params)

    def google_map_link(self, zoom=10):
        params = {
            'q': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.display_name or ''),
            'z': zoom,
        }
        # return 'https://maps.google.com/maps?' + werkzeug.urls.url_encode(params)
        # return 'https://map.baidu.com/search/' + werkzeug.urls.url_encode(params)
        # return 'https://map.baidu.com/?newmap=1&query={}'.format(werkzeug.urls.url_encode(params))
        return "https://map.baidu.com/poi/491%E7%A9%BA%E9%97%B4%E6%B0%B4%E5%8F%B0%E5%B9%BF%E5%9C%BA/@12978624.913896881,4823018.582049059,19z?uid=421ce3191e3cc95b8505bf72&ugc_type=3&ugc_ver=1&device_ratio=1&compat=1&pcevaname=pc4.1&querytype=detailConInfo&da_src=shareurl"


    @api.depends('website_id')
    @api.depends_context('display_website')
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self._context.get('display_website') or not self.env.user.has_group('website.group_multi_website'):
            return
        for partner in self:
            if partner.website_id:
                partner.display_name += f' [{partner.website_id.name}]'
