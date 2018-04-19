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

from urllib import urlencode
from urllib2 import urlopen

import pytest
from wsgi_intercept import (urllib_intercept, add_wsgi_intercept,
                            remove_wsgi_intercept)

from sitescripts.formmail.web.formmail import handleRequest


# We make this a fixture instead of a constant so we can modify it in each
# test as needed without affecting other tests.
@pytest.fixture
def form_data():
    return {
        'name': 'John Doe',
        'email': 'john_doe@gmail.com',
        'subject': 'Hello there!',
        'message': 'Once upon a time\nthere lived a king.',
    }


@pytest.fixture()
def response_for():
    host, port = 'test.local', 80
    urllib_intercept.install_opener()
    add_wsgi_intercept(host, port, lambda: handleRequest)
    url = 'http://{}:{}'.format(host, port)

    def response_for(data):
        if data is None:
            response = urlopen(url)
        else:
            response = urlopen(url, urlencode(data))
        assert response.getcode() == 200
        return response.read()

    yield response_for
    remove_wsgi_intercept()


def test_get_error(response_for):
    assert response_for(None) == 'Unsupported request method'


def test_no_name(response_for, form_data):
    del form_data['name']
    assert response_for(form_data) == 'No name entered'


def test_no_email(response_for, form_data):
    del form_data['email']
    assert response_for(form_data) == 'No email address entered'


def test_no_subject(response_for, form_data):
    del form_data['subject']
    assert response_for(form_data) == 'No subject entered'


def test_no_message(response_for, form_data):
    del form_data['message']
    assert response_for(form_data) == 'No message entered'


def test_bad_email(response_for, form_data):
    form_data['email'] = 'bad_email'
    assert response_for(form_data) == 'Invalid email address'


def test_success(response_for, form_data, mocker):
    sm_mock = mocker.patch('sitescripts.formmail.web.formmail.sendMail')
    assert response_for(form_data) == 'Message sent'
    assert sm_mock.call_count == 1
    params = sm_mock.call_args[0][1]
    assert set(params.keys()) == set(form_data.keys()) | {'time'}
    for key, value in form_data.items():
        assert params[key] == value
