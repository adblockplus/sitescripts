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

import base64
import ConfigParser

import pytest

from sitescripts.reports.web.resolveReport import (
    resolve_report,
    CONF_SECTION,
    CONF_KEY_KEY,
    CONF_URL_KEY,
)

ENCRYPTION_KEY = '12345678901234567890123456789012'
URL_TEMPLATE = 'https://example.com/{report_id}'

PLAINTEXT_GUID = '12345678-1234-1234-1234-123456789abc'
ENCRYPTED_GUID = ('MTIzNDU2Nzg5YWJj,9RuQq5zPNVw2fnjk7zT/jfS+YkDRjWFrly'
                  'YIRRrhdeiuy86yaBq0eqA7iTLwIfjzs1yefw==')

BAD_GUIDS = [
    '',  # Nothing.
    'foobar',  # No comma.
    # Wrong base64 encoding.
    'TIzNDU2Nzg5YWJj,9RuQq5zPNVw2fnjk7zT/jfS+YkDRjWFrly'
    'YIRRrhdeiuy86yaBq0eqA7iTLwIfjzs1yefw==',
    # Wrong nonce.
    'MNIzNDU2Nzg5YWJj,9RuQq5zPNVw2fnjk7zT/jfS+YkDRjWFrly'
    'YIRRrhdeiuy86yaBq0eqA7iTLwIfjzs1yefw==',
]


@pytest.fixture()
def reports_config(mocker):
    """Mock config to override encryption key and redirect URL."""
    mock_config = ConfigParser.ConfigParser()
    mock_config.add_section(CONF_SECTION)
    mock_config.set(CONF_SECTION, CONF_KEY_KEY,
                    base64.b64encode(ENCRYPTION_KEY))
    mock_config.set(CONF_SECTION, CONF_URL_KEY, URL_TEMPLATE)
    mocker.patch('sitescripts.reports.web.resolveReport.get_config',
                 lambda: mock_config)


def test_success(reports_config, mocker):
    start_response_mock = mocker.Mock()
    result = resolve_report({'QUERY_STRING': ENCRYPTED_GUID},
                            start_response_mock)
    assert result == ['Found']
    start_response_mock.assert_called_once_with(
        '302 Found',
        [('Location', URL_TEMPLATE.format(report_id=PLAINTEXT_GUID))],
    )


@pytest.mark.parametrize('guid', BAD_GUIDS)
def test_bad_wrong_guid(reports_config, mocker, guid):
    start_response_mock = mocker.Mock()
    result = resolve_report({'QUERY_STRING': guid},
                            start_response_mock)
    assert result == ['Not Found']
    start_response_mock.assert_called_once_with('404 Not Found', [])
