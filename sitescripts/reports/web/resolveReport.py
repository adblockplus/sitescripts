# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2017-present eyeo GmbH
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

from __future__ import print_function

import base64
import httplib
import sys

from cryptography.hazmat.primitives.ciphers import aead
from cryptography.exceptions import InvalidTag

from sitescripts.utils import get_config
from sitescripts.web import url_handler

CONF_SECTION = 'reports_anonymization'
CONF_KEY_KEY = 'encryption_key'
CONF_URL_KEY = 'redirect_url'


def _decrypt_report_id(guid):
    """Decrypt and verify the report id.

    Returns
    -------
    str or None
        Decrypted id if successfully decrypted, None otherwise.

    """
    config = get_config()
    key = base64.b64decode(config.get(CONF_SECTION, CONF_KEY_KEY))

    # https://cryptography.io/en/latest/hazmat/primitives/aead/
    aes_gcm = aead.AESGCM(key)

    try:
        encoded_nonce, encoded_data = guid.split(',', 1)
        nonce = base64.b64decode(encoded_nonce)
        encypted_data = base64.b64decode(encoded_data)
        return aes_gcm.decrypt(nonce, encypted_data, None)
    except (ValueError, TypeError, InvalidTag):
        print('Invalid guid given to resolveReport:', guid, file=sys.stderr)
        return None


@url_handler('/resolveReport')
def resolve_report(environ, start_response):
    """Decrypt report guid and redirect to report URL."""
    config = get_config()
    redirect_url_template = config.get(CONF_SECTION, CONF_URL_KEY)

    guid = environ.get('QUERY_STRING', '')
    report_id = _decrypt_report_id(guid)

    if report_id is None:
        code, headers = httplib.NOT_FOUND, []
    else:
        location = redirect_url_template.format(report_id=report_id)
        code, headers = httplib.FOUND, [('Location', location)]

    message = httplib.responses[code]
    start_response('{} {}'.format(code, message), headers)
    return [message]
