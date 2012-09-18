# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import re, os, sys
from urlparse import parse_qs
from tempfile import mkstemp
from sitescripts.utils import get_config, setupStderr
from sitescripts.web import url_handler

@url_handler('/submitCrash')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  if not environ.get('HTTP_X_ADBLOCK_PLUS'):
    return showError('Please use Adblock Plus to submit crashes', start_response)

  if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('text/xml'):
    return showError('Unsupported request method', start_response)

  params = parse_qs(environ.get('QUERY_STRING', ''))

  requestVersion = params.get('version', ['0'])[0]
  if requestVersion != '1':
    return showError('Unsupported request version', start_response)

  try:
    request_body_size = int(environ.get('CONTENT_LENGTH', 0))
  except (ValueError):
    return showError('No content', start_response)

  dir = get_config().get('crashes', 'dataPath')
  if not os.path.exists(dir):
    os.makedirs(dir)

  filename = None
  try:
    fd, filename = mkstemp('.xml.tmp', 'crash_', dir)
    file = os.fdopen(fd, 'wb')
    file.write(environ['wsgi.input'].read(request_body_size))
    file.close()
    os.rename(filename, os.path.splitext(filename)[0]);
  except Exception, e:
    if filename != None and os.path.isfile(filename):
      os.remove(filename)
    raise e

  start_response('200 Ok', [('Content-Type', 'text/plain; charset=utf-8')])
  return ['saved'.encode('utf-8')]

def showError(message, start_response):
  start_response('400 Processing Error', [('Content-Type', 'text/plain; charset=utf-8')])
  return [message.encode('utf-8')]
