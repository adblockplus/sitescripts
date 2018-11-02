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

from __future__ import unicode_literals

import subprocess
import pytest
import json

from wsgi_intercept.interceptor import Httplib2Interceptor

import sitescripts.oauth2dl.bin.constants as cnts
from sitescripts.oauth2dl.test.dummy_wsgi_app import main as intercept_app
from sitescripts.oauth2dl.bin.oauth2dl import download_file


def get_valid_keyfile():
    return {
        'private_key_id': 6,
        'private_key': cnts.DUMMY_PRIVATE_KEY,
        'client_email': 'firstpart@secondpart.com',
        'client_id': '8',
        'type': 'service_account',
    }


def get_intercept_app():
    """Return the intercepting WSGI application."""
    return intercept_app


def write_to_json(data, path):
    """Write data to JSON."""
    with open(str(path), 'w') as f:
        json.dump(data, f)


@pytest.fixture
def rootdir(tmpdir):
    """Directory with prepared key and downloadable files."""
    rootdir = tmpdir.join('root')
    rootdir.mkdir()

    # Keyfile missing a key - private_key_id
    invalid_keyfile_path = rootdir.join('keyfile_missing_key.json')
    data = get_valid_keyfile()
    data.pop('private_key')
    write_to_json(data, str(invalid_keyfile_path))

    # Keyfile with invalid private key
    invalid_keyfile_path = rootdir.join('keyfile_invalid_private_key.json')
    data = get_valid_keyfile()
    data['private_key'] = data['private_key'][:-10]
    write_to_json(data, str(invalid_keyfile_path))

    # Keyfile with wrong value for 'type'
    invalid_keyfile_path = rootdir.join('keyfile_invalid_type.json')
    data = get_valid_keyfile()
    data['type'] = 'invalid'
    write_to_json(data, str(invalid_keyfile_path))

    # Valid (dummy) keyfile
    valid_keyfile_path = rootdir.join('good_keyfile.json')
    write_to_json(get_valid_keyfile(), str(valid_keyfile_path))

    # Downloadable file
    rootdir.join('file_to_download').write('Success!')

    # Downloadable file with utf-8 characters
    rootdir.join('file_to_download_utf8').write('Ok \u1234'.encode('utf-8'),
                                                mode='wb')

    return rootdir


@pytest.fixture
def dstfile(tmpdir):
    """Destination file for saving the downloaded whitelist."""
    return tmpdir.join('dst')


def run_script(*args, **kw):
    """Run download script with given arguments and return its output."""
    try:
        cmd = kw.pop('cmd')
    except KeyError:
        cmd = 'python -m sitescripts.oauth2dl.bin.oauth2dl'

    cmd = [cmd] + list(args)
    cmd = ' '.join(cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=True, **kw)

    stdout, stderr = proc.communicate()

    return proc.returncode, stderr.decode('utf-8'), stdout.decode('utf-8')


@pytest.mark.parametrize('args_in, expected_stderr, expected_code', [
    ((), 'usage: oauth2dl.py [-h] [-k KEY] [-s SCOPE] [-o O] url', 2),
    (('www.test.com',), cnts.KEYFILE_NOT_FOUND_ERROR, 1),
    (('www.test.com', '-k', 'test.json'), cnts.SCOPE_NOT_FOUND_ERROR, 1),
    (('www.test.com', '-k', 'test.json', '-s', 'test'),
     "No such file or directory: 'test.json'", 1),
])
def test_error_messages(args_in, expected_stderr, expected_code):
    """Testing that appropriate error messages are provided."""
    code, stderr, _ = run_script(*args_in)

    assert code == expected_code
    assert expected_stderr in stderr


def test_extracting_from_environment_vars():
    """Test if it uses the environment variables if none are provided."""
    test_env = {'OAUTH2_KEY': 'env_test.json',
                'OAUTH2_SCOPE': 'env_test_scope'}
    _, stderr, _ = run_script('www.test.com', env=test_env)

    assert cnts.KEYFILE_NOT_FOUND_ERROR not in stderr
    assert cnts.SCOPE_NOT_FOUND_ERROR not in stderr


@pytest.mark.parametrize('key, expected_stderr, expected_code', [
    ('keyfile_missing_key.json', 'Invalid key file format!', 1),
    ('keyfile_invalid_private_key.json', 'invalid_grant: Not a valid email '
                                         'or user ID.', 1),
    ('keyfile_invalid_type.json', "('Unexpected credentials type', u'invalid',"
                                  " 'Expected', 'service_account')", 1),
    ('good_keyfile.json', 'invalid_grant: Not a valid email or user ID.',
     1),
])
def test_keyfile_errors(rootdir, key, expected_stderr, expected_code):
    """Testing how the script handles key file-related error messages.

    Connects to the actual google API, using set of dummy key files.
    """
    keyfile_path = rootdir.join(key)

    code, stderr, _ = run_script('www.test.com', '-k', str(keyfile_path), '-s',
                                 'test')

    assert code == expected_code
    assert expected_stderr in stderr


@pytest.mark.xfail
@pytest.mark.parametrize('file, expected', [
    ('file_to_download', 'Success!'),
    ('file_to_download_utf8', '\u1234'),
])
def test_download(rootdir, file, expected):
    """Test authenticating and downloading a file.

    Uses a local server that simulates the interaction with the google API
    """
    keyfile_path = str(rootdir.join('good_keyfile.json'))
    url = 'https://www.googleapis.com/download?path={0}'.format(
        str(rootdir.join(file)),
    )
    scope = 'www.googleapis.com'

    with Httplib2Interceptor(get_intercept_app, host='oauth2.googleapis.com',
                             port=443):
        _, data = download_file(url, keyfile_path, scope)

    assert expected in data


@pytest.mark.xfail
def test_download_wrong_url(rootdir):
    """Test authenticating and trying to download a file from an invalid url.

    Uses a local server that simulates the interaction with the google API.
    """
    keyfile_path = str(rootdir.join('good_keyfile.json'))
    url = 'https://www.googleapis.com/download?path={0}'.format(
        str(rootdir.join('inexistent_file')))
    scope = 'www.googleapis.com'

    with Httplib2Interceptor(get_intercept_app, host='oauth2.googleapis.com',
                             port=443):
        headers, data = download_file(url, keyfile_path, scope)

    assert 'NOT FOUND' in data.upper()
    assert headers['status'] == '404'
