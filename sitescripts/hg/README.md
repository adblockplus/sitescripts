# Mercurial hooks

`sitescripts/hg` contains Mercurial hooks for integration with other components
of our infrastructure.

## IRC integration

`irchook.py` contains a commit hook that posts the information about new pushed
commits to an IRC channel.

## Trac integration

`update_issues.py` contains a commit hook that recognises issue references in
commit messages and updates referenced issues in the Adblock Plus issue
tracker.

The format of the commit messages is "ISSUE-REFERENCE - MESSAGE" where
ISSUE-REFERENCE is one of "Noissue" or "Issue NUMBER". Several "Issue"
references separated by commas can be present in the same commit message (for
example: "Issue 1, Issue 2 - Two issues"). The hook will post a comment with
the link to the commit into all referenced issues.

### Configuring the repository

The hook should be installed as `changegroup` or `pretxnchangegroup` hook.

    [hooks]
    pretxnchangegroup = python:.../update_issues.py:hook

### Configuring the hooks

The hooks are configured via `sitescripts.ini` in `hg` section. For example:

    [hg]
    trac_xmlrpc_url=https://abpbot:abpbot@issues.adblockplus.org/login/xmlrpc
    issue_url_template=https://issues.adblockplus.org/ticket/{id}

`hg.track_xmlrpc_url` key from is used to determine the address of XMLRPC
interface of Trac and `hg.issue_url_template` as a template for producing links
to the referenced issues that are displayed in the log.

### Python dependencies of the hook

The hook requires `Jinja2`.
