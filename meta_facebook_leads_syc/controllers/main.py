import functools
import logging
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_GRAPH_API_BASE = 'https://graph.facebook.com/'


def fragment_to_query_string(func):
    @functools.wraps(func)
    def wrapper(self, *a, **kw):
        kw.pop('debug', False)
        if not kw:
            return """<html><head><script>
                var l = window.location;
                var q = l.hash.substring(1);
                var r = l.pathname + l.search;
                if(q.length !== 0) {
                    var s = l.search ? (l.search === '?' ? '' : '&') : '?';
                    r = l.pathname + l.search + s + q;
                }
                if (r == l.pathname) {
                    r = '/';
                }
                window.location = r;
            </script></head><body></body></html>"""
        return func(self, *a, **kw)
    return wrapper


class OAuthController(http.Controller):

    @http.route('/crm_facebook_leads/auth', type='http', auth='user', csrf=False)
    @fragment_to_query_string
    def add_access_token(self, **kw):
        if kw.get('access_token'):
            get_param = request.env['ir.config_parameter'].sudo().get_param
            version = get_param('meta_facebook_leads_syc.crm_fb_api_version', 'v21.0')
            params = {
                'client_id': get_param('meta_facebook_leads_syc.crm_fb_app_id'),
                'client_secret': get_param('meta_facebook_leads_syc.crm_fb_app_secret'),
                'fb_exchange_token': kw.get('access_token'),
            }
            r = requests.get(
                '%s%s/oauth/access_token?grant_type=fb_exchange_token' % (_GRAPH_API_BASE, version),
                params=params,
            ).json()
            if r.get('error'):
                _logger.error(r.get('error', {}).get('message', 'Unknown error'))
            request.env['ir.config_parameter'].sudo().set_param(
                'meta_facebook_leads_syc.crm_fb_access_token',
                r.get('access_token', '')
            )

        return request.redirect('/odoo/settings')
