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

import mock
import unittest

import sitescripts.hg.bin.update_issues as update_issues

def _create_mock_repo(message):
  mock_repo = mock.MagicMock()
  mock_repo.__len__.return_value = 1
  mock_change = mock.MagicMock()
  mock_change.rev.return_value = 0
  mock_change.description.return_value = message
  mock_repo.__getitem__.return_value = mock_change
  return mock_repo

class TestUpdateIssues(unittest.TestCase):
  def setUp(self):
    self.ui = mock.Mock()

  @mock.patch("xmlrpclib.ServerProxy")
  def test_commits_with_invalid_message_format_ignored(self,
                                                       mock_server_proxy):
    messages = ["", "Issue #1337", "Tissue 1337", "Issue 13b"]
    for message in messages:
      mock_repo = _create_mock_repo(message)
      update_issues.hook(self.ui, mock_repo, 0)
      self.ui.warn.assert_called_once()
      self.assertFalse(mock_server_proxy.called)
      self.ui.warn.reset_mock()

  @mock.patch("xmlrpclib.ServerProxy")
  def test_noissue_commits_ignored(self, mock_server_proxy):
    messages = ["Noissue", "noissue"]
    for message in messages:
      mock_repo = _create_mock_repo(message)
      update_issues.hook(self.ui, mock_repo, 0)
      self.assertFalse(self.ui.warn.called)
      self.assertFalse(mock_server_proxy.called)

  @mock.patch("xmlrpclib.ServerProxy")
  def test_single_issue_referenced(self, mock_server_proxy):
    server_proxy_instance = mock_server_proxy.return_value
    messages = ["Issue 1337", "issue 1337"]
    for message in messages:
      mock_repo = _create_mock_repo(message)
      update_issues.hook(self.ui, mock_repo, 0)
      self.assertFalse(self.ui.warn.called)
      server_proxy_instance.ticket.update.assert_called_once()
      self.assertEqual(server_proxy_instance.ticket.update.call_args[0][0],
                       1337)
      server_proxy_instance.reset_mock()

  @mock.patch("xmlrpclib.ServerProxy")
  def test_multiple_issues_referenced(self, mock_server_proxy):
    server_proxy_instance = mock_server_proxy.return_value
    mock_repo = _create_mock_repo("Issue 1337, issue 2448")
    update_issues.hook(self.ui, mock_repo, 0)
    self.assertFalse(self.ui.warn.called)
    calls = server_proxy_instance.ticket.update.call_args_list
    self.assertEqual(len(calls), 2)
    self.assertEqual(calls[0][0][0], 1337)
    self.assertEqual(calls[1][0][0], 2448)

if __name__ == "__main__":
  unittest.main()
