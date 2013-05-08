# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2013 Eyeo GmbH
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
  try:
    file = open(path + '.tmp', 'wb')
    iter = dataIterator(environ['wsgi.input'], file)
    knownIssues = knownIssuesParser.findMatches(iter, params.get('lang', ['en-US'])[0])
    file.close()

    os.rename(path + '.tmp', path);
  except Exception, e:
    if os.path.isfile(path + '.tmp'):
      os.remove(path + '.tmp')
    raise e

  template = get_template(get_config().get('reports', 'submitResponseTemplate'))
  start_response('200 OK', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
  return [template.render({'url': get_config().get('reports', 'urlRoot') + guid, 'knownIssues': knownIssues}).encode('utf-8')]

def showError(message, start_response):
  template = get_template(get_config().get('reports', 'errorTemplate'))
  start_response('400 Processing Error', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
  return [template.render({'message': message}).encode('utf-8')]
