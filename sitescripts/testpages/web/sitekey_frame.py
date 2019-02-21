# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-present eyeo GmbH
#
# Adblock Plus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# Adblock Plus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adblock Plus.  If not, see <http://www.gnu.org/licenses/>.

import base64
import M2Crypto
import os

from sitescripts.utils import get_config, get_template
from sitescripts.web import url_handler, request_path


@url_handler('/sitekey-frame')
def sitekey_frame(environ, start_response):
    template_path, template_file = os.path.split(
        get_config().get('testpages', 'sitekeyFrameTemplate'),
    )
    template = get_template(template_file, template_path=template_path)

    http_path = request_path(environ)
    http_host = environ['HTTP_HOST']
    http_ua = environ['HTTP_USER_AGENT']

    key = M2Crypto.EVP.load_key(get_config().get('testpages', 'sitekeyPath'))
    key.sign_init()
    key.sign_update('\x00'.join([http_path, http_host, http_ua]))
    public_key = base64.b64encode(key.as_der())
    signature = base64.b64encode(key.final())

    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('X-Adblock-Key', '%s_%s' % (public_key, signature)),
    ])
    return [template.render({
        'public_key': public_key,
        'signature': signature,
        'http_path': http_path,
        'http_host': http_host,
        'http_ua': http_ua,
    }).encode('utf-8')]
