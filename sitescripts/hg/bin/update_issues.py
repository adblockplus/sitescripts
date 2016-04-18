# This file is part of Adblock Plus <https://adblockplus.org/>,
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

"""
This module implements a changegroup (or pretxnchangegroup) hook that inspects
all commit messages and checks if issues from the Adblock Plus issue tracker are
being referenced. If there are, it updates them with the respective changeset
URLs.
"""

import posixpath
import re
import xmlrpclib

from sitescripts.utils import get_config, get_template


def _generate_comments(repository_name, changes_by_issue):
    comments = {}
    template = get_template("hg/template/issue_commit_comment.tmpl",
                            autoescape=False)
    for issue_id, changes in changes_by_issue.iteritems():
        comments[issue_id] = template.render({"repository_name": repository_name,
                                              "changes": changes})
    return comments


def _post_comment(issue_id, comment):
    issue_id = int(issue_id)
    url = get_config().get("hg", "trac_xmlrpc_url")
    server = xmlrpclib.ServerProxy(url)
    attributes = server.ticket.get(issue_id)[3]
    server.ticket.update(issue_id, comment,
                         {"_ts": attributes["_ts"], "action": "leave"}, True)


def hook(ui, repo, node, **kwargs):
    first_change = repo[node]
    issue_number_regex = re.compile(r"\bissue\s+(\d+)\b", re.I)
    noissue_regex = re.compile(r"^noissue\b", re.I)
    changes_by_issue = {}
    for revision in xrange(first_change.rev(), len(repo)):
        change = repo[revision]
        description = change.description()
        issue_ids = issue_number_regex.findall(description)
        if issue_ids:
            for issue_id in issue_ids:
                changes_by_issue.setdefault(issue_id, []).append(change)
        elif not noissue_regex.search(description):
            # We should just reject all changes when one of them has an invalid
            # commit message format, see: https://issues.adblockplus.org/ticket/3679
            ui.warn("warning: invalid commit message format in changeset %s\n" %
                    change)

    repository_name = posixpath.split(repo.url())[1]
    comments = _generate_comments(repository_name, changes_by_issue)

    issue_url_template = get_config().get("hg", "issue_url_template")
    for issue_id, comment in comments.iteritems():
        try:
            _post_comment(issue_id, comment)
            ui.status("updating %s\n" % issue_url_template.format(id=issue_id))
        except:
            ui.warn("warning: failed to update %s\n" %
                    issue_url_template.format(id=issue_id))
