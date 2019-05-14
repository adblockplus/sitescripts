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
# along with Adblock Plus. If not, see <http://www.gnu.org/licenses/>.

"""A changegroup (or pretxnchangegroup) hook for Trac integration.

Checks commit messages for issue references and posts comments linking to the
commits into referenced issues.
"""

import collections
import posixpath
import re
import xmlrpclib

from sitescripts.utils import get_config, get_template


ISSUE_NUMBER_REGEX = re.compile(r'\bissue\s+(\d+)\b', re.I)
NOISSUE_REGEX = re.compile(r'^noissue\b', re.I)


def _format_description(change):
    lines = change.description().splitlines()
    message = lines[0].rstrip()
    if len(lines) == 1 or lines[1].strip() == '':
        return message
    return message.rstrip('.') + '...'


def _generate_comments(repository_name, changes_by_issue):
    comments = {}
    template = get_template('hg/template/issue_commit_comment.tmpl',
                            autoescape=False)
    for issue_id, changes in changes_by_issue.items():
        comments[issue_id] = template.render({
            'repository_name': repository_name,
            'changes': changes,
            'format_description': _format_description,
        })
    return comments


def _post_comment(issue_id, comment):
    issue_id = int(issue_id)
    url = get_config().get('hg', 'trac_xmlrpc_url')
    server = xmlrpclib.ServerProxy(url)
    attributes = server.ticket.get(issue_id)[3]
    server.ticket.update(
        issue_id,
        comment,
        {
            '_ts': attributes['_ts'],
            'action': 'leave',
        },
        True,
    )


def hook(ui, repo, node, **kwargs):
    """Post commit references into Trac issues."""
    changes_by_issue = collections.defaultdict(list)

    first_rev = repo[node].rev()
    commits = repo[first_rev:]
    for commit in commits:
        description = commit.description()
        issue_ids = ISSUE_NUMBER_REGEX.findall(description)
        if issue_ids:
            for issue_id in issue_ids:
                changes_by_issue[issue_id].append(commit)
        elif not NOISSUE_REGEX.search(description):
            ui.warn('warning: invalid commit message format in changeset {}\n'
                    .format(commit))

    repository_name = posixpath.split(repo.url())[1]
    comments = _generate_comments(repository_name, changes_by_issue)

    issue_url_template = get_config().get('hg', 'issue_url_template')
    for issue_id, comment in comments.items():
        issue_url = issue_url_template.format(id=issue_id)
        ui.status('updating {}\n'.format(issue_url))
        try:
            _post_comment(issue_id, comment)
        except Exception as exc:
            ui.warn('warning: failed to update {}\n'.format(issue_url))
            ui.warn('error message: {}\n'.format(exc))
