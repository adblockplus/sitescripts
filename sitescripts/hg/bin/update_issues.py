# This file is part of Adblock Plus <https://adblockplus.org/>,
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

"""Hooks for integrating Mercurial with Trac.

Update the issues that are referenced in commit messages when the commits
are pushed and `master` bookmark is moved. See README.md for more
information on behavior and configuration.
"""

import collections
import contextlib
import posixpath
import re
import xmlrpclib

from sitescripts.utils import get_config, get_template


_IssueRef = collections.namedtuple('IssueRef', 'id commits is_fixed')

ISSUE_NUMBER_REGEX = re.compile(r'\b(issue|fixes)\s+(\d+)\b', re.I)
NOISSUE_REGEX = re.compile(r'^noissue\b', re.I)
COMMIT_MESSAGE_REGEX = re.compile(r'\[\S+\ ([^\]]+)\]')


@contextlib.contextmanager
def _trac_proxy(ui, config, action_descr):
    trac_url = config.get('hg', 'trac_xmlrpc_url')
    try:
        yield xmlrpclib.ServerProxy(trac_url)
    except Exception as exc:
        if getattr(exc, 'faultCode', 0) == 404:
            ui.warn('warning: 404 (not found) while {}\n'.format(action_descr))
        else:
            ui.warn('error: {} while {}\n'.format(exc, action_descr))


def _update_issue(ui, config, issue_id, changes, comment=''):
    issue_url_template = config.get('hg', 'issue_url_template')
    issue_url = issue_url_template.format(id=issue_id)

    updates = []
    if comment:
        for message in COMMIT_MESSAGE_REGEX.findall(comment):
            updates.append(' - referenced a commit: ' + message)
    if 'milestone' in changes:
        updates.append(' - set milestone to ' + changes['milestone'])
    if changes['action'] == 'resolve':
        updates.append(' - closed')
    if not updates:
        return

    with _trac_proxy(ui, config, 'updating issue {}'.format(issue_id)) as tp:
        tp.ticket.update(issue_id, comment, changes, True)
        ui.status('updated {}:\n{}\n'.format(issue_url, '\n'.join(updates)))


def _format_description(change):
    lines = change.description().splitlines()
    message = lines[0].rstrip()
    if len(lines) == 1 or lines[1].strip() == '':
        return message
    return message.rstrip('.') + '...'


def _post_comments(ui, repo, config, refs):
    repo_name = posixpath.split(repo.url())[1]
    template = get_template('hg/template/issue_commit_comment.tmpl',
                            autoescape=False)
    for ref in refs:
        comment_text = template.render({
            'repository_name': repo_name,
            'changes': ref.commits,
            'format_description': _format_description,
        })
        with _trac_proxy(ui, config, 'getting issue {}'.format(ref.id)) as tp:
            attrs = tp.ticket.get(ref.id)[3]
            changes = {'_ts': attrs['_ts'], 'action': 'leave'}
            _update_issue(ui, config, ref.id, changes, comment_text)


def _compile_module_regexps(ui, config, modules):
    for module, regexp in config.items('hg_module_milestones'):
        try:
            yield module, re.compile('^{}$'.format(regexp), re.I)
        except Exception as exc:
            ui.warn('warning: skipped invalid regexp for module {} in '
                    "[hg_module_milestones] config: '{}' ({})\n"
                    .format(module, regexp, exc))


def _get_module_milestones(ui, config, modules):
    module_regexps = dict(_compile_module_regexps(ui, config, modules))
    modules = module_regexps.keys()
    if not modules:
        return []

    milestones_by_module = {}
    with _trac_proxy(ui, config, 'getting milestones') as tp:
        milestone_names = [
            name for name in tp.ticket.milestone.getAll()
            if any(regexp.search(name) for regexp in module_regexps.values())
        ]
        # Using a MultiCall is better because we might have many milestones.
        get_milestones = xmlrpclib.MultiCall(tp)
        for name in milestone_names:
            get_milestones.ticket.milestone.get(name)
        milestones = [ms for ms in get_milestones() if not ms['completed']]
        for module in modules:
            for milestone in milestones:
                if module_regexps[module].search(milestone['name']):
                    milestones_by_module[module] = milestone['name']
                    break

    return milestones_by_module.items()


def _declare_fixed(ui, config, refs):
    updates = []
    # Changes that need milestones added to them, indexed by module.
    need_milestones = collections.defaultdict(list)

    for ref in refs:
        with _trac_proxy(ui, config, 'getting issue {}'.format(ref.id)) as tp:
            attrs = tp.ticket.get(ref.id)[3]
            changes = {
                '_ts': attrs['_ts'],
                'action': 'leave',
            }
            actions = tp.ticket.getActions(ref.id)
            if any(action[0] == 'resolve' for action in actions):
                changes['action'] = 'resolve'
            if not attrs['milestone']:
                need_milestones[attrs['component']].append(changes)
            updates.append((ref.id, changes))

    for module, milestone in _get_module_milestones(ui, config,
                                                    need_milestones.keys()):
        for changes in need_milestones[module]:
            changes['milestone'] = milestone

    for issue_id, changes in updates:
        _update_issue(ui, config, issue_id, changes)


def _collect_references(ui, commits):
    commits_by_issue = collections.defaultdict(list)
    fixed_issues = set()

    for commit in commits:
        message = commit.description()
        if ' - ' not in message:
            ui.warn("warning: invalid commit message format: '{}'\n"
                    .format(message))
            continue

        refs, rest = message.split(' - ', 1)
        issue_refs = ISSUE_NUMBER_REGEX.findall(refs)
        if issue_refs:
            for ref_type, issue_id in issue_refs:
                issue_id = int(issue_id)
                commits_by_issue[issue_id].append(commit)
                if ref_type.lower() == 'fixes':
                    fixed_issues.add(issue_id)
        elif not NOISSUE_REGEX.search(refs):
            ui.warn("warning: no issue reference in commit message: '{}'\n"
                    .format(message))

    for issue_id, commits in sorted(commits_by_issue.items()):
        yield _IssueRef(issue_id, commits, is_fixed=issue_id in fixed_issues)


def changegroup_hook(ui, repo, node, **kwargs):
    config = get_config()
    first_rev = repo[node].rev()
    pushed_commits = repo[first_rev:]
    refs = _collect_references(ui, pushed_commits)
    _post_comments(ui, repo, config, refs)


def pushkey_hook(ui, repo, **kwargs):
    if (kwargs['namespace'] != 'bookmarks' or  # Not a bookmark move.
            kwargs['key'] != 'master' or       # Not `master` bookmark.
            not kwargs['old']):                # The bookmark is just created.
        return

    config = get_config()
    old_master_rev = repo[kwargs['old']].rev()
    new_master_rev = repo[kwargs['new']].rev()
    added_revs = repo.changelog.findmissingrevs([old_master_rev],
                                                [new_master_rev])
    added_commits = [repo[rev] for rev in added_revs]
    refs = [ref for ref in _collect_references(ui, added_commits)
            if ref.is_fixed]
    _declare_fixed(ui, config, refs)


# Alias for backward compatibility.
hook = changegroup_hook
