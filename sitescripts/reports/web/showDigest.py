# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import re, os, sys, hashlib, Cookie
from datetime import date, timedelta, datetime
from urlparse import parse_qs
from sitescripts.reports.utils import getDigestSecret, getDigestSecret_compat
from sitescripts.utils import get_config, get_template, setupStderr
from sitescripts.web import url_handler

@url_handler('/digest')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  params = parse_qs(environ.get('QUERY_STRING', ''))

  id = params.get('id', [''])[0].lower()
  if not re.match(r'^[\da-f]{32}$', id):
    return showError('Invalid or missing ID', start_response)
  
  thisweek = getDigestSecret(id, date.today().isocalendar())
  prevweek = getDigestSecret(id, (date.today()-timedelta(weeks=1)).isocalendar())
  thisweek_compat = getDigestSecret_compat(id, date.today().isocalendar())
  prevweek_compat = getDigestSecret_compat(id, (date.today()-timedelta(weeks=1)).isocalendar())

  redirect = False
  secret = params.get('secret', [''])[0].lower()
  if secret:
    redirect = True
  else:
    try:
      cookies = Cookie.SimpleCookie(environ.get('HTTP_COOKIE', ''))
      secret = cookies[id].value
    except (Cookie.CookieError, KeyError):
      return showError('No digest secret', start_response)

  if secret != thisweek and secret != prevweek and secret != thisweek_compat and secret != prevweek_compat:
    return showError('Wrong secret', start_response)

  path = os.path.join(get_config().get('reports', 'digestPath'), id + '.html')
  if not os.path.exists(path):
    return showError('Digest doesn\'t exist', start_response)
    
  cookies = Cookie.SimpleCookie()
  cookies[id] = secret
  cookies[id]['path'] = '/'
  cookies[id]['secure'] = True
  cookies[id]['httponly'] = True
  expiration = datetime.utcnow() + timedelta(weeks=2)
  cookies[id]['expires'] = expiration.strftime('%a, %d-%b-%Y %H:%M:%S GMT')
  if redirect:
    start_response('302 Found', [('Location', '/digest?id=' + id), ('Set-Cookie', cookies[id].OutputString())])
    return []
  else:
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8'), ('Set-Cookie', cookies[id].OutputString())])
    blockSize = 4096
    f = open(path)
    if 'wsgi.file_wrapper' in environ:
      return environ['wsgi.file_wrapper'](f, blockSize)
    else:
      return iter(lambda: f.read(blockSize), '')

def showError(message, start_response):
  template = get_template(get_config().get('reports', 'errorTemplate'))
  start_response('400 Processing Error', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
  return [template.render({'message': message}).encode('utf-8')]
