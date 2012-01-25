# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import re, os, sys, hashlib
from datetime import date, timedelta
from urlparse import parse_qs
from sitescripts.utils import get_config, get_template, setupStderr
from sitescripts.web import url_handler

@url_handler('/digest')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  params = parse_qs(environ.get('QUERY_STRING', ''))

  id = params.get('id', [''])[0].lower()
  if not re.match(r'^[\da-f]{32}$', id):
    return showError('Invalid or missing ID', start_response)
  
  thisweek = getWeekSecret(id, date.today().isocalendar())
  prevweek = getWeekSecret(id, (date.today()-timedelta(weeks=1)).isocalendar())

  secret = params.get('secret', [''])[0].lower()
  if secret != thisweek and secret != prevweek:
    return showError('Wrong secret', start_response)

  path = os.path.join(get_config().get('reports', 'digestPath'), id + '.html')
  if not os.path.exists(path):
    return showError('Digest doesn\'t exist', start_response)

  start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
  blockSize = 4096
  f = open(path)
  if 'wsgi.file_wrapper' in environ:
    return environ['wsgi.file_wrapper'](f, blockSize)
  else:
    return iter(lambda: f.read(blockSize), '')

def getWeekSecret(id, (year, week, weekday)):
  hash = hashlib.md5()
  hash.update(get_config().get('reports', 'secret'))
  hash.update(id)
  hash.update(str(year))
  hash.update(str(week))
  return hash.hexdigest()

def showError(message, start_response):
  template = get_template(get_config().get('reports', 'errorTemplate'))
  start_response('400 Processing Error', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
  return [template.render({'message': message}).encode('utf-8')]
