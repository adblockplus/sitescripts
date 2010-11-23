# coding=utf-8

from time import time
from urlparse import urlparse, parse_qs
import subprocess, sys, os, re
from sitescripts.utils import get_config, cached, setupStderr

def handleSubscriptionFallbackRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  (redirects, gone)= getData()

  start_response('200 OK', [('Content-Type', 'text/plain')])

  url = None
  params = parse_qs(environ.get('QUERY_STRING', ''))
  if 'url' in params:
    url = params['url'][0]

  if url and url in gone:
    return ['410']
  elif url and url in redirects:
    return ['301 %s' % redirects[url]]

  return []

@cached(600)
def getData():
  repoPath = os.path.abspath(get_config().get('subscriptions', 'repository'))
  processed = set()

  (redirectData, errors) = subprocess.Popen(['hg', '-R', repoPath, 'cat', '-r', 'tip', os.path.join(repoPath, 'redirects')], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors
  redirects = processData(redirectData, processed, {})

  (goneData, errors) = subprocess.Popen(['hg', '-R', repoPath, 'cat', '-r', 'tip', os.path.join(repoPath, 'gone')], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors
  gone = processData(goneData, processed, set())

  return (redirects, gone)

def processData(data, processed, var):
  data = data.replace('\r', '')
  data = data.split('\n')

  currentTarget = None
  for line in data:
    line = line.strip()
    if line == '':
      continue

    match = re.match(r'^\[(.+)\]$', line)
    if match:
      currentTarget = match.group(1)
      urlData = urlparse(currentTarget)
      if urlData.scheme != 'http' and urlData.scheme != 'https':
        print >>sys.stderr, 'Redirect to a non-HTTP URL: %s' % currentTarget
      continue

    urlData = urlparse(line)
    if urlData.scheme != 'http' and urlData.scheme != 'https':
      print >>sys.stderr, 'Redirect for a non-HTTP URL: %s' % line

    if not isinstance(var, set) and not currentTarget:
      print >>sys.stderr, 'Redirect without a target: %s' % line
    if isinstance(var, set) and currentTarget:
      print >>sys.stderr, 'Gone entry with a target: %s' % line
    if line in processed:
      print >>sys.stderr, 'Multiple instructions for URL %s' % line

    if isinstance(var, set):
      var.add(line)
    else:
      var[line] = currentTarget

  return var
