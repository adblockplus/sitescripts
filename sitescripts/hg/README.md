# Mercurial hooks

`sitescripts/hg` contains Mercurial hooks for integration with other components
of our infrastructure.

## IRC integration

`irchook.py` contains a commit hook that posts the information about new pushed
commits to an IRC channel. 

## Trac integration

`update_issues.py` contains two hooks: `changegroup_hook` and `pushkey_hook`.
They will recognise issue references in commit messages and update referenced
issues in the Adblock Plus issue tracker.

The format of the commit messages is "ISSUE-REFERENCE - MESSAGE"
where ISSUE-REFERENCE is one of "Noissue", "Issue NUMBER" or "Fixes NUMBER".
Several "Issue" and "Fixes" references separated by commas can be present
in the same commit message (for example: "Issue 1, Fixes 2 - Two issues").
Such commit will affect all the referenced issues.

* `changegroup_hook` will post a comment with the link to the commit into the
  issue if the issue is referenced from the commit message.
* `pushkey_hook` will close the issues and assign milestones to them (based
  on their module) when the `master` bookmark passes over the commits that fix
  them. It will not assign a milestone if the issue already has one.

### Configuring the repository

`changegroup_hook` should be installed as `changegroup` or
`pretxnchangegroup` hook. `pushkey_hook` should be installed as
`pushkey` or `prepushkey` hook. For example (in `.hg/hgrc`):

    [hooks]
    pretxnchangegroup = python:.../update_issues.py:changegroup_hook
    pushkey = python:.../update_issues.py:pushkey_hook

### Configuring the hooks

The hooks are configured via `sitescripts.ini` in `hg` and
`hg_module_milestones` sections. For example:

    [hg]
    trac_xmlrpc_url=https://abpbot:abpbot@issues.adblockplus.org/login/xmlrpc
    issue_url_template=https://issues.adblockplus.org/ticket/{id}

    [hg_module_milestones]
    platform=adblock-plus(-[\d\.]+)?-for-chrome-opera-safari(-next)?
    Adblock-Plus-for-Firefox=adblock-plus(-[\d\.]+)?-for-firefox(-next)?

`hg.track_xmlrpc_url` key from is used to determine the address of XMLRPC
interface of Trac and `hg.issue_url_template` as a template for producing links
to the referenced issues that are displayed in the log.

The keys of the `hg_module_milestones` section are module names and the values
are corresponding milestone regular expressions (they are matched
case-insensitively). The first open milestone that matches the regular
expression of the issue's module will be assigned to the issue when the
`master` bookmark passes a commit that fixes it.

### Master bookmark

What exactly does it mean when we say _`master` bookmark is passing a commit_?
The idea is that if the `master` bookmark _passed_ a commit we will have
those changes in our working copy when we do `hg checkout master`.

Let's first look at a simple case, linear commit history like this:

    one <- two <- three

Here `one` is a parent commit of `two` and `two` is a parent of `three`. If
the `master` bookmark was on `one` and then moved to `three`, we say that it
passed `two` and `three`. This would happen naturally if we clone the
repository that contains `one` with the `master` bookmark pointing to it,
check out `master`, author two commits and then push them.

A somewhat similar thing happens when we have branches:

    one <---- two <---- three
         \            /
          \-- dos <--/

Here `one` is a parent commit of `two` and `dos` and they are both parents
of `three`. If the `master` bookmark was on `two` and now is on `three`,
we say that it passed `three` and `dos`. What happened here is that by `three`
we've merged a branch containing `dos` into the master branch that was going
through `one` and `two`.
