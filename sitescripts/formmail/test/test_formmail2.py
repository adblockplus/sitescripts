# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2017 eyeo GmbH
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
from urllib2 import urlopen, HTTPError

import pytest
from wsgi_intercept import (urllib_intercept, add_wsgi_intercept,
                            remove_wsgi_intercept)

from sitescripts.formmail.web import formmail2


@pytest.fixture()
def form_config():
    return formmail2.conf_parse(formmail2.get_config_items())['test']


@pytest.fixture()
def form_handler(form_config):
    return formmail2.make_handler('test', form_config)[1]


# We make this a fixture instead of a constant so we can modify it in each
# test as needed without affecting other tests.
@pytest.fixture
def form_data():
    return {
        'email': 'john_doe@gmail.com',
        'mandatory': 'john_doe@gmail.com',
        'non_mandatory_message': 'Once upon a time\nthere lived a king.',
        'non_mandatory_email': 'test@test.com'
    }


@pytest.fixture()
def response_for(form_handler):
    host, port = 'test.local', 80
    urllib_intercept.install_opener()
    add_wsgi_intercept(host, port, lambda: form_handler)
    url = 'http://{}:{}'.format(host, port)

    def response_for(data):
        if data is None:
            response = urlopen(url)
        else:
            response = urlopen(url, urlencode(data))
        return response.code, response.read()

    yield response_for
    remove_wsgi_intercept()


def test_form_handler_email_errors(form_config):
    tmp_config = form_config
    del tmp_config['url'].value
    with pytest.raises(Exception) as error:
        formmail2.make_handler('test', tmp_config)[1]
    assert error.value.message == 'No URL configured for form handler: test'


def test_form_handler_field_errors(form_config):
    tmp_config = form_config
    tmp_config['fields'] = {}
    with pytest.raises(Exception) as error:
        formmail2.make_handler('test', tmp_config)[1]
    assert error.value.message == 'No fields configured for form handler: test'

    del tmp_config['fields']
    with pytest.raises(Exception) as error:
        formmail2.make_handler('test', tmp_config)[1]
    assert error.value.message == 'No fields configured for form handler: test'


def test_form_handler_template_errors(form_config):
    tmp_config = form_config
    tmp_config['template'].value = 'no'
    with pytest.raises(Exception) as error:
        formmail2.make_handler('test', tmp_config)[1]
    assert error.typename == 'TemplateNotFound'

    del tmp_config['template'].value
    with pytest.raises(Exception) as error:
        formmail2.make_handler('test', tmp_config)[1]
    assert error.value.message == ('No template configured for form handler'
                                   ': test')
    del tmp_config['template']
    with pytest.raises(Exception) as error:
        formmail2.make_handler('test', tmp_config)[1]
    assert error.value.message == ('No template configured for form handler'
                                   ': test')


def test_config_parse(form_config):
    assert form_config['url'].value == 'test/apply/submit'
    assert form_config['fields']['email'].value == 'mandatory, email'


def test_success(response_for, form_data, mocker):
    sm_mock = mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    assert response_for(form_data) == (200, '')
    assert sm_mock.call_count == 1
    params = sm_mock.call_args[0][1]['fields']
    assert set(params.keys()) == set(form_data.keys())
    for key, value in form_data.items():
        assert params[key] == value


def test_non_mandatory_no_msg(response_for, form_data, mocker):
    mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    form_data['non_mandatory'] = ''
    assert response_for(form_data) == (200, '')


def test_invalid_email_cstm_msg(response_for, form_data, mocker, form_config):
    mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    form_data['email'] = 'bademail'
    with pytest.raises(HTTPError) as error:
        response_for(form_data)
    assert error.value.read() == 'You failed the email validation'


def test_valid_nan_mandatory_email(response_for, form_data, mocker):
    mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    form_data['non_mandatory_email'] = 'asfaf'
    with pytest.raises(HTTPError) as error:
        response_for(form_data)
    assert error.value.read() == 'Invalid email'

    del form_data['non_mandatory_email']
    assert response_for(form_data) == (200, '')


def test_mandatory_fail_dflt_msg(response_for, form_data, mocker):
    mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    del form_data['mandatory']
    with pytest.raises(HTTPError) as error:
        response_for(form_data)
    assert error.value.read() == 'No mandatory entered'
