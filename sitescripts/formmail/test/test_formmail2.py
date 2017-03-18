# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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

from sitescripts.formmail.web import formmail2

HOST = 'test.local'
LOG_PORT = 80
NO_LOG_PORT = 81


@pytest.fixture
def log_path(tmpdir):
    return str(tmpdir.join('test.csv_log'))


@pytest.fixture
def log_form_config():
    return formmail2.conf_parse(formmail2.get_config_items())['test']


@pytest.fixture
def form_config():
    config = formmail2.conf_parse(formmail2.get_config_items())['test']
    del config['csv_log']
    return config


@pytest.fixture
def form_handler(log_path, form_config, log_form_config):
    """ Create two handlers, one that logs and another that doesn't """
    log_form_config['csv_log'].value = log_path
    return (formmail2.make_handler('test', log_form_config)[1],
            formmail2.make_handler('test', form_config)[1])


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


@pytest.fixture
def response_for(form_handler):
    """ Registers two intercepts, returns responses for them based on bool """
    urllib_intercept.install_opener()
    add_wsgi_intercept(HOST, LOG_PORT, lambda: form_handler[0])
    add_wsgi_intercept(HOST, NO_LOG_PORT, lambda: form_handler[1])

    def response_for(data, log=False):
        url = 'http://{}:{}'.format(HOST, NO_LOG_PORT)
        if log:
            url = 'http://{}:{}'.format(HOST, LOG_PORT)
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


def test_sendmail_fail(log_path, response_for, form_data, mocker):
    sm_mock = mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    sm_mock.side_effect = Exception('Sendmail Fail')
    with pytest.raises(HTTPError) as error:
        response_for(form_data, log=True)
    assert error.typename == 'HTTPError'

    with open(log_path) as log_file:
        row = DictReader(log_file).next()
        assert 'time' in row


@pytest.mark.parametrize('log, res',
                         [(True, (200, '')), (False, (200, ''))])
def test_utf8_success(log, res, log_path, response_for, form_data, mocker):
    """ DictWriter does not accpet utf-8, call log handler """
    form_data['non_mandatory_message'] = '\xc3\xb6'
    sm_mock = mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    assert response_for(form_data, log) == res
    assert sm_mock.call_count == 1
    params = sm_mock.call_args[0][1]['fields']
    assert set(params.keys()) == set(form_data.keys())
    for key, value in form_data.items():
        assert params[key] == value.decode('utf8')


def test_success(response_for, form_data, mocker):
    sm_mock = mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    assert response_for(form_data) == (200, '')
    assert sm_mock.call_count == 1
    params = sm_mock.call_args[0][1]['fields']
    assert set(params.keys()) == set(form_data.keys())
    for key, value in form_data.items():
        assert params[key] == value


def test_log_success(log_path, response_for, form_data, mocker):
    sm_mock = mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    assert response_for(form_data, log=True) == (200, '')
    assert sm_mock.call_count == 1
    params = sm_mock.call_args[0][1]['fields']
    assert set(params.keys()) == set(form_data.keys())
    for key, value in form_data.items():
        assert params[key] == value
    with open(log_path) as log_file:
        row = DictReader(log_file).next()
        assert 'time' in row


def test_log_append_success(log_path, response_for, form_data, mocker):
    sm_mock = mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    assert response_for(form_data, log=True) == (200, '')
    form_data['non_mandatory_message'] = ''
    assert response_for(form_data, log=True) == (200, '')
    assert sm_mock.call_count == 2
    params = sm_mock.call_args[0][1]['fields']
    assert set(params.keys()) == set(form_data.keys())
    for key, value in form_data.items():
        assert params[key] == value
    with open(log_path) as log_file:
        reader = DictReader(log_file)
        row = reader.next()
        assert row != reader.next()


def test_non_mandatory_no_msg(response_for, form_data, mocker):
    mocker.patch('sitescripts.formmail.web.formmail2.sendMail')
    form_data['non_mandatory_message'] = ''
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


def test_field_err(form_config, form_data, log_path):
    """ Submits a form that does not have the dame fields as previous submissions

    that have the same form name, asserts that proper message is returned and
    the row was properly written
    """
    formmail2.log_formdata(form_data, log_path)
    del(form_config['fields']['email'])
    del(form_data['email'])
    try:
        formmail2.log_formdata(form_data, log_path)
    except Exception as e:
        assert e.message == ('Field names have changed, error log '
                             'written to {}_error').format(log_path)

    with open(log_path+'_error') as error_log:
        assert DictReader(error_log).next() == form_data


def test_append_field_err(form_config, form_data, log_path):
    """ Submits two identical forms that do not match the previous fields

    found in the log file, triggering two rows to be added to the error
    log and asserting the proper message is returned and that the rows
    were written as expected
    """
    formmail2.log_formdata(form_data, log_path)
    del(form_config['fields']['email'])
    del(form_data['email'])
    try:
        formmail2.log_formdata(form_data, log_path)
    except Exception:
        pass
    try:
        formmail2.log_formdata(form_data, log_path)
    except Exception as e:
        assert e.message == ('Field names have changed, error log'
                             ' appended to {}_error').format(log_path)

    with open(log_path+'_error') as error_log:
        reader = DictReader(error_log)
        # two identical rows should be in the error log
        assert reader.next() == form_data
        assert reader.next() == form_data
