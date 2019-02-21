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
import sys
import urllib2

from wsgi_intercept import (urllib_intercept, add_wsgi_intercept,
                            remove_wsgi_intercept)

# Fake import M2Crypto so that we don't need to install the real thing for this
# test where we don't want encryption anyway.
sys.modules['M2Crypto'] = sys

from sitescripts.testpages.web import sitekey_frame


# Request parameters.
HOST = 'test.local'
SCRIPT_NAME = 'sitekey-frame'
USER_AGENT = 'foobar'

# This is the string that should be signed by the web handler.
TO_SIGN = '/{}\x00{}\x00{}'.format(SCRIPT_NAME, HOST, USER_AGENT)


class FakeTemplate:
    """Jinja template replacement for testing."""

    def __init__(self, *args, **kw):
        pass

    def render(self, params):
        """Stringify the parameters."""
        return str(params)


class FakeM2Crypto:
    """M2Crypto replacement for testing."""

    class EVP:
        @staticmethod
        def load_key(path):
            return FakeM2Crypto()

    def sign_init(self):
        pass

    def sign_update(self, data):
        self.data = data

    def as_der(self):
        return 'key'

    def final(self):
        return self.data


MODULE = 'sitescripts.testpages.web.sitekey_frame'


def test_sitekey_frame(mocker):
    mocker.patch(MODULE + '.get_template', FakeTemplate)
    mocker.patch(MODULE + '.M2Crypto', FakeM2Crypto)

    urllib_intercept.install_opener()
    add_wsgi_intercept(HOST, 80, lambda: sitekey_frame.sitekey_frame,
                       script_name=SCRIPT_NAME)
    try:
        response = urllib2.urlopen(urllib2.Request(
            'http://{}/{}'.format(HOST, SCRIPT_NAME),
            headers={'User-Agent': 'foobar'},
        ))
        assert response.code == 200
        data = eval(response.read())
        assert base64.b64decode(data['signature']) == TO_SIGN
        assert data['http_path'] == '/' + SCRIPT_NAME
        assert data['http_host'] == HOST
        assert data['http_ua'] == USER_AGENT
    finally:
        remove_wsgi_intercept()
