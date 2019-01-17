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
from urllib2 import urlopen, HTTPError
from csv import DictReader

import pytest
from wsgi_intercept import (urllib_intercept, add_wsgi_intercept,
                            remove_wsgi_intercept)

from sitescripts.formmail.web import formmail

HOST = 'test.local'
LOG_PORT = 80
NO_LOG_PORT = 81


@pytest.fixture
def log_path(tmpdir):
    return str(tmpdir.join('test.csv_log'))


@pytest.fixture
def log_form_config():
    return formmail.conf_parse(formmail.get_config_items())['test']


@pytest.fixture
def form_config():
    config = formmail.conf_parse(formmail.get_config_items())['test']
    del config['csv_log']
    return config


@pytest.fixture
def form_handler(log_path, form_config, log_form_config):
    """ Create two handlers, one that logs and another that doesn't """
    log_form_config['csv_log'].value = log_path
    return (formmail.make_handler('test', log_form_config)[1],
            formmail.make_handler('test', form_config)[1])


# We make this a fixture instead of a constant so we can modify it in each
# test as needed without affecting other tests.
@pytest.fixture
def form_data():
    return {
        'email': 'john_doe@gmail.com',
        'mandatory': 'john_doe@gmail.com',
        'non_mandatory_message': 'Once upon a time\nthere lived a king.',
        'non_mandatory_email': 'test@test.com',
    }


@pytest.fixture
def response_for(form_handler):
    """ Registers two intercepts, returns responses for them based on bool """
    urllib_intercept.install_opener()
    add_wsgi_intercept(HOST, LOG_PORT, lambda: form_handler[0])
    add_wsgi_intercept(HOST, NO_LOG_PORT, lambda: form_handler[1])

    def response_for(data, log=False):
        if log:
            url = 'http://{}:{}'.format(HOST, LOG_PORT)
        else:
            url = 'http://{}:{}'.format(HOST, NO_LOG_PORT)
        if data is None:
            response = urlopen(url)
        else:
            response = urlopen(url, urlencode(data))
        return response.code, response.read()

    yield response_for
    remove_wsgi_intercept()


@pytest.fixture
def sm_mock(mocker):
    return mocker.patch('sitescripts.formmail.web.formmail.sendMail')


@pytest.mark.parametrize('key,message', [
    ('url', 'No URL configured for form handler: test'),
    ('fields', 'No fields configured for form handler: test'),
    ('template', 'No template configured for form handler: test'),
])
def test_config_errors(key, message, form_config):
    del form_config[key]
    with pytest.raises(Exception) as error:
        formmail.make_handler('test', form_config)[1]
    assert str(error.value) == message


@pytest.mark.parametrize('field,message', [
    (('new_field', 'foo'), 'Unexpected field/fields: new_field'),
    (('mandatory', ''), 'No mandatory entered'),
    (('non_mandatory_email', 'asfaf'), 'Invalid email'),
    (('email', 'asfaf'), 'You failed the email validation'),
    (('email', ''), 'You failed the email test'),
])
def test_http_errs(field, message, response_for, form_data, sm_mock):
    key, value = field
    form_data[key] = value
    with pytest.raises(HTTPError) as error:
        response_for(form_data)
    assert error.value.read() == message


@pytest.mark.parametrize('field,expected', [
    (('non_mandatory_message', '\xc3\xb6'), (200, '')),
    (('non_mandatory_message', ''), (200, '')),
])
def test_success(field, expected, log_path, response_for, form_data, sm_mock):
    key, value = field
    form_data[key] = value
    assert response_for(form_data, log=False) == expected
    assert sm_mock.call_count == 1

    params = sm_mock.call_args[0][1]['fields']
    assert set(params.keys()) == set(form_data.keys())
    for key, value in form_data.items():
        assert params[key] == value.decode('utf8')

    assert response_for(form_data, log=True) == expected
    assert sm_mock.call_count == 2

    assert response_for(form_data, log=True) == expected
    assert sm_mock.call_count == 3

    with open(log_path) as log_file:
        reader = DictReader(log_file)
        row = reader.next()
        # rows should not be equal because the time field
        # is added by the logging function.
        assert row != reader.next()


def test_config_field_errors(form_config):
    form_config['fields'] = {}
    with pytest.raises(Exception) as error:
        formmail.make_handler('test', form_config)[1]
    assert str(error.value) == 'No fields configured for form handler: test'


def test_config_template_errors(form_config):
    form_config['template'].value = 'no'
    with pytest.raises(Exception) as error:
        formmail.make_handler('test', form_config)[1]
    assert str(error.value) == 'Template not found at: no'


def test_config_parse(form_config):
    assert form_config['url'].value == 'test/apply/submit'
    assert form_config['fields']['email'].value == 'mandatory, email'


def test_sendmail_fail(log_path, response_for, form_data, sm_mock):
    sm_mock.side_effect = Exception('Sendmail Fail')
    with pytest.raises(HTTPError):
        response_for(form_data, log=True)

    with open(log_path) as log_file:
        row = DictReader(log_file).next()
        assert row != form_data


def test_append_field_err(form_config, form_data, log_path):
    """ Checks that error logs are correctly written and appended

    Submits three forms, the second two have different fields to the first
    and should be added to the same log file as each other, and be identical
    """
    formmail.log_formdata(form_data, log_path)
    del form_data['email']

    # submit two forms with fields that dont match the config
    # this should append the second form to the error log file
    with pytest.raises(Exception):
        formmail.log_formdata(form_data, log_path)
    with pytest.raises(Exception):
        formmail.log_formdata(form_data, log_path)

    with open(log_path + '_error') as error_log:
        reader = DictReader(error_log)
        assert reader.next() == form_data
        assert reader.next() == form_data
