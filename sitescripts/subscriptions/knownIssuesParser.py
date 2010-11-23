# coding: utf-8

import subprocess, sys, os, re
from sitescripts.utils import get_config, cached

supportedKeys = {
  'type': ('report', 'type'),
  'abpversion': ('adblock-plus', 'version'),
  'abpbuild': ('adblock-plus', 'build'),
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
  'mainURL': ('window', 'url'),
  'frameURL': ('frame', 'url'),
  'openerURL': ('window', 'opener'),
  'requestLocation': ('request', 'location'),
  'requestDomain': ('request', 'docDomain'),
  'filterText': ('filter', 'text'),
  'subscriptionURL': ('subscription', 'id'),
  'extension': ('extension', 'id version'),
  'errorText': ('error', 'text'),
  'errorLocation': ('error', 'file line'),
}

class Ruleset:
  def __init__(self, name):
    self._rules = []
    self.name = name

  def addRule(self, rule):
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
    if len(value) > 2 and value[0] == '/' and value[len(value) - 1] == '/':
      self.pattern = re.compile(value[1:len(value)-1])
      self.isRegExp = True
    else:
      self.pattern = value
      self.isRegExp = False

  def checkMatch(self, value):
    if self.matched:
      return

    if self.isRegExp:
      self.matched = re.search(self.pattern, value)
    else:
      self.matched = (self.pattern == value)

def resetMatches(rules):
  for ruleGroup in rules.itervalues():
    for rule in ruleGroup.itervalues():
      rule.matched = False

def getRule(rules, key, value):
  global supportedKeys

  if not key in supportedKeys:
    print >>sys.stderr, 'Unsupported key "%s"' % key
    return None

  if not key in rules:
    rules[key] = {}
  if not value in rules[key]:
    rules[key][value] = Rule(key, value)
  return rules[key][value]

def checkMatch(rules, key, value):
  value = value.lower()
  if key in rules:
    for rule in rules[key].itervalues():
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

  (data, errors) = subprocess.Popen(['hg', '-R', repoPath, 'cat', '-r', 'tip', os.path.join(repoPath, 'knownIssues')], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors

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
      ruleset = Ruleset(line[1:len(line)-1])
    else:
      if ruleset == None:
        print >>sys.stderr, 'Found line %s before start of a ruleset' % line
        continue
      if line.find('=') < 0:
        print >>sys.stderr, 'Unrecognized line %s' % line
        continue
      (key, value) = line.split('=', 1)
      key = key.rstrip()
      value = value.lstrip()
      if key == 'url':
        ruleset.url = value
      else:
        rule = getRule(rules, key, value)
        if rule:
          ruleset.addRule(rule)
  return (rules, rulesets)

def findMatches(it, lang):
  global supportedKeys

  (rules, rulesets) = getRules()

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
        (requiredTag, requiredAttrs, requiredValue) = t
      else:
        (requiredTag, requiredAttrs) = t
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
