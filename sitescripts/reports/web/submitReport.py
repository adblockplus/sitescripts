# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import re, os, sys
from urlparse import parse_qs
from sitescripts.utils import get_config, get_template, setupStderr
from sitescripts.web import url_handler
import sitescripts.subscriptions.knownIssuesParser as knownIssuesParser

def dataIterator(source, file):
  for line in source:
    file.write(line)
    yield line

@url_handler('/submitReport')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  if not environ.get('HTTP_X_ADBLOCK_PLUS'):
    return showError('Please use Adblock Plus to submit reports', start_response)

  if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('text/xml'):
    return showError('Unsupported request method', start_response)

  params = parse_qs(environ.get('QUERY_STRING', ''))

  requestVersion = params.get('version', ['0'])[0]
  if requestVersion != '1':
    return showError('Unsupported request version', start_response)

  guid = params.get('guid', [''])[0].lower()
  if not re.match(r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$', guid):
    return showError('Invalid or missing GUID', start_response)

  path = os.path.join(get_config().get('reports', 'dataPath'), guid + '.xml')
  if os.path.exists(path) or os.path.exists(path + '.tmp'):
    return showError('Duplicate GUID', start_response)

  dir = os.path.dirname(path)
  if not os.path.exists(dir):
    os.makedirs(dir)
  file = open(path + '.tmp', 'wb')
  iter = dataIterator(environ['wsgi.input'], file)
  knownIssues = knownIssuesParser.findMatches(iter, params.get('lang', ['en-US'])[0])
  file.close()

  os.rename(path + '.tmp', path);

  template = get_template(get_config().get('reports', 'submitResponseTemplate'))
  start_response('200 OK', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
  return [template.render({'url': get_config().get('reports', 'urlRoot') + guid, 'knownIssues': knownIssues}).encode('utf-8')]

def showError(message, start_response):
  template = get_template(get_config().get('reports', 'errorTemplate'))
  start_response('400 Processing Error', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
  return [template.render({'message': message}).encode('utf-8')]
