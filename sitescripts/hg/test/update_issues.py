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

import ConfigParser
import mock
import unittest

import sitescripts.hg.bin.update_issues as update_issues


def _issue(component, milestone='', can_resolve=False):
    issue = {
        'attrs': {'_ts': 1, 'milestone': milestone, 'component': component},
        'actions': [['leave', '', '', []]],
    }
    if can_resolve:
        issue['actions'].append(['resolve', '', '', []])
    return issue


ISSUES = {
    1337: _issue(component='one', can_resolve=True),
    2448: _issue(component='two'),
    3559: _issue(component='one', milestone='other'),
    4670: _issue(component='three', can_resolve=True),
    5781: _issue(component='four', can_resolve=True),
}

MILESTONES = {
    'completed': {'completed': True, 'name': 'completed'},
    'current': {'completed': None, 'name': 'current'},
    'other': {'completed': None, 'name': 'other'},
}


class _TestBase(unittest.TestCase):
    """Base class for hook tests that prepares the environment."""

    def _patchWith(self, target, return_value):
        patcher = mock.patch(target, return_value=return_value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _create_mock_milestone_multicall(self):
        ret = []
        multicall = mock.Mock(return_value=ret)
        multicall.ticket.milestone.get = lambda i: ret.append(MILESTONES[i])
        return multicall

    def _mock_trac(self):
        trac = mock.Mock()
        trac.ticket.get = lambda i: [i, mock.ANY, mock.ANY, ISSUES[i]['attrs']]
        trac.ticket.getActions = lambda i: ISSUES[i]['actions']
        trac.ticket.milestone.getAll = lambda: sorted(MILESTONES.keys())
        self.trac_proxy_mock = trac
        self._patchWith('xmlrpclib.ServerProxy', trac)
        self._patchWith('xmlrpclib.MultiCall',
                        self._create_mock_milestone_multicall())

    def _mock_config(self):
        config = ConfigParser.ConfigParser()
        config.add_section('hg')
        config.set('hg', 'trac_xmlrpc_url', 'foo')
        config.set('hg', 'issue_url_template', '#{id}')
        config.add_section('hg_module_milestones')
        config.set('hg_module_milestones', 'one', '.*')
        config.set('hg_module_milestones', 'two', 'other')
        config.set('hg_module_milestones', 'four', 'completed')
        self._patchWith('sitescripts.hg.bin.update_issues.get_config', config)

    def setUp(self):
        self.ui = mock.Mock()
        self._mock_trac()
        self._mock_config()


class _MockRepo(list):
    def __init__(self, commit_messages):
        list.__init__(self)
        for i, message in enumerate(commit_messages):
            mock_commit = mock.MagicMock()
            mock_commit.rev.return_value = i
            mock_commit.hex.return_value = '{:010x}'.format(i) + '0' * 30
            mock_commit.description.return_value = message
            self.append(mock_commit)
        self.changelog = mock.Mock()
        self.changelog.findmissingrevs = self._findmissingrevs

    def _findmissingrevs(self, olds, news):
        return range(olds[0] + 1, news[0] + 1)

    def __getitem__(self, commit_id):
        if isinstance(commit_id, str):
            return [commit for commit in self if commit.hex() == commit_id][0]
        return list.__getitem__(self, commit_id)

    def url(self):
        return 'mock/repo'


class TestChangegroupHook(_TestBase):

    def _run_hook(self, commit_messages, warning_count=0, update_count=0):
        repo = _MockRepo(commit_messages)
        update_issues.changegroup_hook(self.ui, repo, 0)
        warnings = self.ui.warn.call_args_list
        updates = self.trac_proxy_mock.ticket.update.call_args_list
        self.assertEqual(len(warnings), warning_count)
        self.assertEqual(len(updates), update_count)
        return updates

    def test_commits_with_invalid_message_format_ignored(self):
        self._run_hook([
            '',
            'Issue #1337 - Extraneous characters in issue number',
            'Issue 1337',  # No dash, no message.
            'Issue 1337: Colon instead of dash',
            'Noissue no dash',
            'Issue 1337-No space around dash',
            'Fixes 1337 no dash',
        ], warning_count=7)

    def test_noissue_commits_ignored(self):
        self._run_hook(['Noissue - Foo', 'noissue - Bar'])  # No updates.

    def test_single_issue_referenced(self):
        updates = self._run_hook(['Issue 1337 - Foo'], update_count=1)
        self.assertEqual(updates[0][0][0], 1337)

    def test_multiline_commit_message(self):
        updates = self._run_hook(['Issue 1337 - Foo\nBar',
                                  'Issue 1337 - Bar.\nBaz',
                                  'Fixes 2448 - Foo\n\nBar',
                                  'Fixes 2448 - Bar\n \nBaz'],
                                 update_count=2)
        comment_1337 = updates[0][0][1]
        self.assertIn('Issue 1337 - Foo...]', comment_1337)
        self.assertIn('Issue 1337 - Bar...]', comment_1337)
        comment_2448 = updates[1][0][1]
        self.assertIn('Fixes 2448 - Foo]', comment_2448)
        self.assertIn('Fixes 2448 - Bar]', comment_2448)

    def test_multiline_commit_message_crlf(self):
        updates = self._run_hook(['Issue 1337 - Foo\r\nBar',
                                  'Issue 1337 - Bar.\r\nBaz',
                                  'Fixes 2448 - Foo\r\n\r\nBar',
                                  'Fixes 2448 - Bar\r\n \r\nBaz'],
                                 update_count=2)
        comment_1337 = updates[0][0][1]
        self.assertIn('Issue 1337 - Foo...]', comment_1337)
        self.assertIn('Issue 1337 - Bar...]', comment_1337)
        comment_2448 = updates[1][0][1]
        self.assertIn('Fixes 2448 - Foo]', comment_2448)
        self.assertIn('Fixes 2448 - Bar]', comment_2448)

    def test_missing_issue_referenced(self):
        self._run_hook(['Issue 42 - Bar'], warning_count=1)

    def test_multiple_issues_referenced(self):
        updates = self._run_hook(['Issue 1337, fixes 2448 - Foo'],
                                 update_count=2)
        self.assertEqual(updates[0][0][0], 1337)
        self.assertEqual(updates[1][0][0], 2448)

    def test_multiple_commits_for_issue(self):
        updates = self._run_hook(['Issue 1337 - Foo', 'Fixes 1337 - Bar'],
                                 update_count=1)
        comment = updates[0][0][1]
        self.assertIn('000000000000', comment)
        self.assertIn('000000000100', comment)


class TestPushkeyHook(_TestBase):

    def _run_hook(self, commit_messages, bookmark='master',
                  warning_count=0, update_count=0):
        repo = _MockRepo(['Base', 'Old'] + commit_messages)
        update_issues.pushkey_hook(self.ui, repo,
                                   namespace='bookmarks', key=bookmark,
                                   old=1, new=1 + len(commit_messages))
        warnings = self.ui.warn.call_args_list
        updates = self.trac_proxy_mock.ticket.update.call_args_list
        self.assertEqual(len(warnings), warning_count)
        self.assertEqual(len(updates), update_count)
        return updates

    def _check_update(self, update, issue_id, action='resolve',
                      milestone='current'):
        self.assertEqual(update[0][0], issue_id)
        changes = update[0][2]
        self.assertEqual(changes['action'], action)
        if milestone is None:
            self.assertNotIn('milestone', changes)
        else:
            self.assertEqual(changes['milestone'], milestone)

    def test_move_other_bookmark(self):
        self._run_hook(['Fixes 1337 - Foo'], bookmark='other')  # No updates.

    def test_one_issue_fixed(self):
        updates = self._run_hook(['Fixes 1337 - Foo'], update_count=1)
        self._check_update(updates[0], 1337)

    def test_fix_closed_issue(self):
        updates = self._run_hook(['fixes 2448 - Foo'], update_count=1)
        self._check_update(updates[0], 2448, action='leave', milestone='other')

    def test_fix_issue_noregexp(self):
        updates = self._run_hook(['Fixes 4670 - Foo'], update_count=1)
        self._check_update(updates[0], 4670, milestone=None)

    def test_fix_issue_no_matching_milestones(self):
        updates = self._run_hook(['Fixes 5781 - Foo'], update_count=1)
        self._check_update(updates[0], 5781, milestone=None)

    def test_fix_many(self):
        updates = self._run_hook(['Fixes 1337 - Foo', 'Fixes 2448 - Bar'],
                                 update_count=2)
        self._check_update(updates[0], 1337)
        self._check_update(updates[1], 2448, action='leave', milestone='other')

    def test_fix_nonexistent(self):
        self._run_hook(['Fixes 7331 - Foo'], warning_count=1)

    def test_fix_closed_with_assigned_milestone(self):
        self._run_hook(['fixes 3559 - Foo'])  # No updates.


if __name__ == '__main__':
    unittest.main()
