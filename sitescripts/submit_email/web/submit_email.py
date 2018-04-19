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

import fcntl
import hmac
import hashlib
import wsgiref.util
import ConfigParser
from urlparse import parse_qsl, urljoin
from urllib import urlencode, quote

from sitescripts.utils import get_config, sendMail, encode_email_address
from sitescripts.web import url_handler, form_handler, send_simple_response

VERIFICATION_PATH = '/verifyEmail'


def sign(config, data):
    secret = config.get('submit_email', 'secret')
    return hmac.new(secret, data, hashlib.sha1).hexdigest()


@url_handler('/submitEmail')
@form_handler
def submit_email(environ, start_response, data):
    config = get_config()

    try:
        product = data['product']
        template = config.get('submit_email', product + '_verification_email_template')
    except (KeyError, ConfigParser.NoOptionError):
        return send_simple_response(start_response, 400, 'Unknown product')

    email = data.get('email', '').strip()
    try:
        email = encode_email_address(email)
    except ValueError:
        return send_simple_response(
            start_response, 400,
            'Please enter a valid email address.',
        )

    params = [('email', email), ('signature', sign(config, email)), ('product', product)]
    lang = data.get('lang')
    if lang:
        params.append(('lang', lang))

    sendMail(
        template,
        {
            'recipient': email,
            'verification_url': '%s?%s' % (
                urljoin(wsgiref.util.application_uri(environ), VERIFICATION_PATH),
                urlencode(params),
            ),
        },
    )

    return send_simple_response(
        start_response, 200,
        'A confirmation email has been sent. Please check '
        'your email and click the confirmation link.',
    )


@url_handler(VERIFICATION_PATH)
def verify_email(environ, start_response):
    config = get_config()
    params = dict(parse_qsl(environ.get('QUERY_STRING', '')))

    try:
        filename = config.get('submit_email', params['product'] + '_filename')
    except (KeyError, ConfigParser.NoOptionError):
        return send_simple_response(start_response, 400, 'Unknown product')

    email = params.get('email', '')
    signature = params.get('signature', '')
    if sign(config, email) != signature:
        return send_simple_response(
            start_response, 403,
            'Invalid signature in verification request.',
        )

    with open(filename, 'ab', 0) as file:
        fcntl.lockf(file, fcntl.LOCK_EX)
        try:
            print >>file, email
        finally:
            fcntl.lockf(file, fcntl.LOCK_UN)

    location = config.get('submit_email', 'successful_verification_redirect_location')
    location = location.format(lang=quote(params.get('lang') or 'en', ''))
    start_response('303 See Other', [('Location', location)])
    return []
