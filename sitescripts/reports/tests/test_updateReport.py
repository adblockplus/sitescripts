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

import sys
from urllib import urlencode
from urllib2 import urlopen, HTTPError

import pytest
from wsgi_intercept import (urllib_intercept, add_wsgi_intercept,
                            remove_wsgi_intercept)

# We are mocking the functions that use MySQLdb, so it is not needed. This
# is to prevent the tests from crashing when they try to import it.
sys.modules['MySQLdb'] = sys
from sitescripts.reports.web.updateReport import handleRequest

LOCAL_HOST = 'test.local'
REMOTE_HOST = 'reports.adblockplus.org'
PORT = 80
PLAINTEXT_GUID = '12345678-1234-1234-1234-123456789abc'
UR_PATH = 'sitescripts.reports.web.updateReport.'


def intercept_fn(environ, start_response):
    assert environ['SERVER_NAME'] == REMOTE_HOST
    assert PLAINTEXT_GUID in environ['PATH_INFO']
    return 'Intercepted!'


@pytest.fixture
def response_for():
    """Register two intercepts, and return responses for them."""
    urllib_intercept.install_opener()
    add_wsgi_intercept(LOCAL_HOST, PORT, lambda: handleRequest)
    add_wsgi_intercept(REMOTE_HOST, 443, lambda: intercept_fn)

    def response_for(data):
        url = 'http://{}:{}'.format(LOCAL_HOST, PORT)
        response = urlopen(url, urlencode(data))
        return response.code, response.read()

    yield response_for
    remove_wsgi_intercept()


@pytest.fixture
def form_data():
    return {
        'email': 'jane_doe@example.com',
        'secret': '92b3e705f2abe74c20c1c5ea9abd9ba2',
        'guid': PLAINTEXT_GUID,
        'status': 'x' * 1025,
        'usefulness': 0,
        'notify': 'test NOTIFY',
        'message': 'test MESSAGE',
        'subject': 'test SUBJECT',
        'name': 'test NAME',
    }


@pytest.mark.parametrize('field,message', [
    (('guid', 'badGUID'), 'Invalid or missing report GUID'),
    (('secret', 'badSECRET'), 'Wrong secret value'),
])
def test_http_errs(field, message, response_for, form_data, mocker):
    mocker.patch(UR_PATH + 'getReport', new=lambda *args: {'usefulness': 1})
    key, value = field
    form_data[key] = value
    with pytest.raises(HTTPError) as error:
        response_for(form_data)

    assert message in error.value.read()


def test_success(response_for, form_data, mocker):
    # These methods are patched to avoid the need for a MySQL database
    mocker.patch(UR_PATH + 'getReport', new=lambda *args: {'usefulness': 1,
                 'email': 'jane_doe@example.com'})
    sr_mock = mocker.patch(UR_PATH + 'saveReport')
    uuu_mock = mocker.patch(UR_PATH + 'updateUserUsefulness')
    sun_mock = mocker.patch(UR_PATH + 'sendUpdateNotification')

    assert response_for(form_data) == (200, '\nIntercepted!')

    assert sr_mock.call_count == 1
    for key in ['usefulness', 'email']:
        assert key in sr_mock.call_args[0][1]
        assert sr_mock.call_args[0][1][key] == str(form_data[key])

    assert '0' in uuu_mock.call_args[0] and 1 in uuu_mock.call_args[0]

    for key in ['email', 'status']:
        assert key in sun_mock.call_args[0][0]
    assert sun_mock.call_args[0][0]['email'] == form_data['email']

    # These should not be equal, because updateReport.py strips characters
    # over 1024, and form_data['status'] has 1025.
    assert str(sr_mock.call_args[0][1]['status']) != form_data['status']
    assert str(sun_mock.call_args[0][0]['status']) != form_data['status']


def test_get_report_error(response_for, form_data, mocker):
    mocker.patch(UR_PATH + 'getReport', new=lambda *args: None)
    with pytest.raises(HTTPError) as error:
        response_for(form_data)

    assert 'Report does not exist' in error.value.read()
