# coding=utf-8

import re, sys, os, subprocess
from urlparse import urlparse
from tempfile import mkdtemp
from shutil import rmtree
import eventlet
from eventlet.green import urllib2
from sitescripts.utils import get_config, get_template, setupStderr

def checkURL(url):
  try:
    result = urllib2.urlopen(url, timeout=60).read(1)
    return (url, True)
  except urllib2.HTTPError, e:
    return (url, e.code)
  except:
    return (url, False)

def checkSite(site):
  try:
    result = urllib2.urlopen('http://downforeveryoneorjustme.com/' + site, timeout=60).read()
    if re.search(r'\blooks down\b', result):
      return (site, False)
    else:
      return (site, True)
  except:
    return (site, True)

def checkSubscriptions(repo):
  tempDir = mkdtemp()
  checkoutDir = os.path.join(tempDir, 'subscriptionlist')

  (dummy, errors) = subprocess.Popen(['hg', 'clone', repo, checkoutDir], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors

  sys.path.append(checkoutDir)
  import subscriptionParser
  subscriptions = subscriptionParser.parseDir(checkoutDir).values()
  subscriptions.sort(key=lambda s: s.name.lower())

  urls = {}
  sites = {}
  for subscription in subscriptions:
    for key in ('homepage', 'forum', 'blog', 'faq', 'contact', 'changelog'):
      url = getattr(subscription, key)
      if url != None:
        urls[url] = True
    for (title, url, complete) in subscription.variants:
      urls[url] = True

  pool = eventlet.GreenPool()
  for (url, result) in pool.imap(checkURL, urls.iterkeys()):
    urls[url] = result
    if result == False:
      sites[urlparse(url).netloc] = True
  for (site, result) in pool.imap(checkSite, sites.iterkeys()):
    sites[site] = result

  result = []
  for subscription in subscriptions:
    s = {'name': subscription.name, 'links': []}
    result.append(s)
    for key in ('homepage', 'forum', 'blog', 'faq', 'contact', 'changelog'):
      url = getattr(subscription, key)
      if url != None:
        site = urlparse(url).netloc
        s['links'].append({
          'url': url,
          'title': key[0].upper() + key[1:],
          'result': urls[url],
          'siteResult': site in sites and sites[site],
        })
    for (title, url, complete) in subscription.variants:
      site = urlparse(url).netloc
      s['links'].append({
        'url': url,
        'title': title,
        'result': urls[url],
        'siteResult': site in sites and sites[site],
      })
  return result

if __name__ == '__main__':
  setupStderr()

  subscriptions = checkSubscriptions(get_config().get('subscriptions', 'repository'))
  outputFile = get_config().get('subscriptions', 'statusPage')
  template = get_template(get_config().get('subscriptions', 'statusTemplate'))
  template.stream({'subscriptions': subscriptions}).dump(outputFile, encoding='utf-8')
