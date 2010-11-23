# coding: utf-8

import subprocess, sys, os, re, codecs
from urlparse import parse_qsl
from tempfile import mkdtemp
from shutil import rmtree
from gzip import GzipFile
from sitescripts.utils import get_config, setupStderr, sendMail

def countSubscriptionRequests(logPath, counts):
  regexp = re.compile(r'"GET \/getSubscription\?([^" ]*) ')
  f = GzipFile(logPath, 'rb')
  for line in f:
    matches = re.search(regexp, line)
    if matches:
      query = matches.group(1)
      for key, value in parse_qsl(query):
        if key == 'url' and re.match(r'^https?:[\x00-\x7F]+$', value):
          if not value in counts:
            counts[value] = 1
          else:
            counts[value] += 1
          break
  f.close()

def processFile(dir, fileName, counts):
  result = []

  f = codecs.open(os.path.join(dir, fileName), 'rb', encoding='utf-8')
  for line in f:
    line = line.strip()

    if line == '' or line[0] == '[':
      result.append(line)
    else:
      count = 0
      if line in counts:
        count = counts[line]
        del counts[line]
      result.append('%5i %s' % (count, line))

  f.close()
  return result

def loadSubscriptions(repo, counts):
  global interval

  tempDir = mkdtemp()
  checkoutDir = os.path.join(tempDir, 'subscriptionlist')

  (dummy, errors) = subprocess.Popen(['hg', 'clone', repo, checkoutDir], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors

  sys.path.append(checkoutDir)
  import subscriptionParser
  subscriptions = subscriptionParser.parseDir(checkoutDir)

  knownURLs = {}
  for subscription in subscriptions.values():
    for title, url, complete in subscription.variants:
      knownURLs[url] = True

  redirects = processFile(checkoutDir, 'redirects', counts)
  gone = processFile(checkoutDir, 'gone', counts)

  unaccounted = filter(lambda url: counts[url] >= 10, counts.keys())
  unaccounted.sort(key=lambda url: counts[url], reverse=True)
  for i in range(0, len(unaccounted)):
    url = unaccounted[i]
    mark = ' [?]'
    if url in knownURLs:
      mark = ''
    unaccounted[i] = '%5i %s%s' % (counts[url], url, mark)

  rmtree(tempDir, True)

  return (redirects, gone, unaccounted)

if __name__ == '__main__':
  setupStderr()

  counts = {}
  for i in range(1, 15):
    logPath = os.path.join(get_config().get('logs', 'dataPath'), get_config().get('logs', 'fileName') % i)
    countSubscriptionRequests(logPath, counts)

  repoPath = get_config().get('subscriptions', 'repository')
  (redirects, gone, unaccounted) = loadSubscriptions(repoPath, counts)

  sendMail(get_config().get('subscriptions', 'reportTemplate'), {
    'redirects': redirects,
    'gone': gone,
    'unaccounted': unaccounted,
  })
