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

"""Test Mercurial Trac integration hook."""

import mock
import pytest

import sitescripts.hg.bin.update_issues as update_issues

COMMIT_HASH = '000011112222'


class MercurialRepositoryMock(list):

    def __init__(self, message):
        change_mock = mock.MagicMock()
        change_mock.rev.return_value = 0
        change_mock.hex.return_value = COMMIT_HASH
        change_mock.description.return_value = message
        list.__init__(self, [change_mock])

    def url(self):
        return 'repo/mock'


@pytest.fixture
def server_proxy_mock(mocker):
    return mocker.patch('xmlrpclib.ServerProxy')


@pytest.fixture
def ui_mock():
    return mock.MagicMock()


@pytest.mark.parametrize('message', [
    '', 'Issue #1337', 'Tissue 1337', 'Issue 13b',
])
def test_invalid_message_format(message, ui_mock, server_proxy_mock):
    """Check that commits with invalid messages are ignored with a warning."""
    repo_mock = MercurialRepositoryMock(message)
    update_issues.hook(ui_mock, repo_mock, 0)
    ui_mock.warn.assert_called_once()
    assert not server_proxy_mock.called


@pytest.mark.parametrize('message', ['Noissue - foobar', 'noissue'])
def test_noissue(message, ui_mock, server_proxy_mock):
    """Check that noissue commits are ignored without warning."""
    repo_mock = MercurialRepositoryMock(message)
    update_issues.hook(ui_mock, repo_mock, 0)
    assert not ui_mock.warn.called
    assert not server_proxy_mock.called


@pytest.mark.parametrize('message', ['Issue 1337 - foo', 'issue 1337 - foo'])
def test_single_issue(message, ui_mock, server_proxy_mock):
    """Check that a commit referencing a single issue gets linked."""
    server_proxy = server_proxy_mock.return_value
    repo_mock = MercurialRepositoryMock(message)
    update_issues.hook(ui_mock, repo_mock, 0)
    assert not ui_mock.warn.called
    server_proxy.ticket.update.assert_called_once()
    call = server_proxy.ticket.update.call_args
    assert call[0][0] == 1337
    comment = call[0][1]
    assert comment.startswith('A commit referencing this issue has landed')
    assert COMMIT_HASH in comment
    assert comment.endswith('- foo]')


def test_multiple_issues(ui_mock, server_proxy_mock):
    """Check that a commit referencing two issues gets linked twice."""
    server_proxy = server_proxy_mock.return_value
    repo_mock = MercurialRepositoryMock('Issue 1337, issue 2448')
    update_issues.hook(ui_mock, repo_mock, 0)
    assert not ui_mock.warn.called
    calls = server_proxy.ticket.update.call_args_list
    assert len(calls) == 2
    assert calls[0][0][0] == 1337
    assert calls[1][0][0] == 2448
