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

import subprocess
import sys
import os
import re
from sitescripts.utils import get_config, cached

supportedKeys = {
    'type': ('report', 'type'),
    'abpversion': ('adblock-plus', 'version'),
    'abplocale': ('adblock-plus', 'locale'),
    'appname': ('application', 'name'),
    'appvendor': ('application', 'vendor'),
    'appversion': ('application', 'version'),
    'appua': ('application', 'userAgent'),
    'platformname': ('platform', 'name'),
    'platformversion': ('platform', 'version'),
    'platformbuild': ('platform', 'build'),
    'isEnabled': ('option', 'id', 'enabled'),
    'objectTabsEnabled': ('option', 'id', 'objecttabs'),
    'collapseEnabled': ('option', 'id', 'collapse'),
    'privateBrowsingEnabled': ('option', 'id', 'privateBrowsing'),
    'subscriptionsAutoUpdateEnabled': ('option', 'id', 'subscriptionsAutoUpdate'),
    'mainURL': ('window', 'url'),
    'frameURL': ('frame', 'url'),
    'openerURL': ('window', 'opener'),
    'referrerURL': ('window', 'referrer'),
    'requestLocation': ('request', 'location'),
    'requestDomain': ('request', 'docDomain'),
    'filterText': ('filter', 'text'),
    'subscriptionURL': ('subscription', 'id'),
    'subscriptionDownloadStatus': ('subscription', 'downloadStatus'),
    'subscriptionVersion': ('subscription', 'version'),
    'extension': ('extension', 'id version'),
    'errorText': ('error', 'text'),
    'errorLocation': ('error', 'file line'),
}


class Ruleset:
    def __init__(self, name):
        self._rules = []
        self.name = name

    def addRule(self, rules, key, value):
        global supportedKeys

        if not key in supportedKeys:
            print >>sys.stderr, 'Unsupported key "%s"' % key
            return

        for rule in self._rules:
            if rule.key == key:
                rule.addPattern(value)
                return

        rule = Rule(key, value)
        if not key in rules:
            rules[key] = []
        rules[key].append(rule)
        self._rules.append(rule)

    def checkValidity(self):
        if len(self._rules) == 0:
            print >>sys.stderr, 'Ruleset "%s" doesn\'t have any rules defined' % self.name
        if not self.url:
            print >>sys.stderr, 'Ruleset "%s" doesn\'t have a URL defined' % self.name

    @property
    def matched(self):
        for rule in self._rules:
            if not rule.matched:
                return False
        return True

    url = None


class Rule:
    def __init__(self, key, value):
        value = value.lower()

        self.matched = False
        self.key = key
        self.patterns = []
        self.addPattern(value)

    def addPattern(self, value):
        value = value.lower()
        if len(value) > 2 and value[0] == '/' and value[len(value) - 1] == '/':
            self.patterns.append(re.compile(value[1:len(value) - 1]))
        else:
            value = re.sub(r'\*+', r'*', value)      # Remove multiple wildcards
            value = re.sub(r'^\*', r'', value)       # Remove leading wildcards
            value = re.sub(r'\*$', r'', value)       # Remove trailing wildcards
            value = re.sub(r'\^\|$', r'^', value)    # remove anchors following separator placeholder
            value = re.sub(r'(\W)', r'\\\1', value)  # escape special symbols
            value = re.sub(r'\\\*', '.*', value)     # replace wildcards by .*
            # process separator placeholders (all ANSI charaters but alphanumeric characters and _%.-)
            value = re.sub(r'\\\^', r'(?:[\x00-\x24\x26-\x2C\x2F\x3A-\x40\x5B-\x5E\x60\x7B-\x80]|$)', value)
            # process extended anchor at expression start
            value = re.sub(r'^\\\|\\\|', r'^[\w\-]+:/+(?!/)(?:[^/]+\.)?', value)
            value = re.sub(r'^\\\|', r'^', value)    # process anchor at expression start
            value = re.sub(r'\\\|$', r'$', value)    # process anchor at expression end
            self.patterns.append(re.compile(value))

    def checkMatch(self, value):
        if self.matched:
            return

        for pattern in self.patterns:
            if re.search(pattern, value):
                self.matched = True
                break


def resetMatches(rules):
    for ruleGroup in rules.itervalues():
        for rule in ruleGroup:
            rule.matched = False


def checkMatch(rules, key, value):
    value = value.lower()
    if key in rules:
        for rule in rules[key]:
            rule.checkMatch(value)


def extractMatches(rules, rulesets, lang):
    result = {}
    for ruleset in rulesets:
        if ruleset.matched:
            url = re.sub(r'%LANG%', lang, ruleset.url)
            result[url] = True
    resetMatches(rules)

    result = result.keys()
    result.sort()
    return result


@cached(600)
def getRules():
    repoPath = os.path.abspath(get_config().get('subscriptions', 'repository'))

    data = subprocess.check_output(['hg', '-R', repoPath, 'cat', '-r', 'default', os.path.join(repoPath, 'knownIssues')])
    data = data.decode('utf-8').replace('\r', '').split('\n')
    data.append('[]')   # Pushes out last section

    rules = {}
    rulesets = []

    ruleset = None
    for line in data:
        commentIndex = line.find('#')
        if commentIndex >= 0:
            line = line[0:commentIndex]
        line = line.strip()
        if line == '':
            continue

        if line[0] == '[' and line[len(line) - 1] == ']':
            if ruleset:
                ruleset.checkValidity()
                rulesets.append(ruleset)
            ruleset = Ruleset(line[1:len(line) - 1])
        else:
            if ruleset == None:
                print >>sys.stderr, 'Found line %s before start of a ruleset' % line
                continue
            if line.find('=') < 0:
                print >>sys.stderr, 'Unrecognized line %s' % line
                continue
            key, value = line.split('=', 1)
            key = key.rstrip()
            value = value.lstrip()
            if key == 'url':
                ruleset.url = value
            else:
                ruleset.addRule(rules, key, value)
    return (rules, rulesets)


def findMatches(it, lang):
    global supportedKeys

    rules, rulesets = getRules()

    for line in it:
        match = re.search(r'<([\w\-]+)\s*(.*?)\s*/?>([^<>]*)', line)
        if not match:
            continue

        tag = match.group(1)
        attrText = match.group(2)
        text = match.group(3).strip()

        attrs = {}
        for match in re.finditer(r'(\w+)="([^"]*)"', attrText):
            attrs[match.group(1)] = match.group(2).strip().replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&')

        for key, t in supportedKeys.iteritems():
            if len(t) == 3:
                requiredTag, requiredAttrs, requiredValue = t
            else:
                requiredTag, requiredAttrs = t
                requiredValue = None
            requiredAttrs = requiredAttrs.split(' ')
            if requiredTag != tag:
                continue

            foundAttrs = []
            for attr in requiredAttrs:
                if attr in attrs:
                    foundAttrs.append(attrs[attr])
            if len(foundAttrs) != len(requiredAttrs):
                continue

            value = ' '.join(foundAttrs)
            if requiredValue != None:
                if requiredValue != value:
                    continue
                value = text

            checkMatch(rules, key, value)
    return extractMatches(rules, rulesets, lang)
