# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import re
from urlparse import parse_qsl
from sitescripts.utils import get_config, sendMail, setupStderr
from sitescripts.web import url_handler

@url_handler('/formmail')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
  if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
    return 'Unsupported request method'

  try:
    request_body_length = int(environ['CONTENT_LENGTH'])
  except:
    return 'Invalid or missing Content-Length header'

  request_body = environ['wsgi.input'].read(request_body_length)
  params = {}
  for key, value in parse_qsl(request_body):
    params[key] = value.decode('utf-8').strip()

  if not 'name' in params or params['name'] == '':
    return 'No name entered'
  if not 'email' in params or params['email'] == '':
    return 'No email address entered'
  if not 'subject' in params or params['subject'] == '':
    return 'No subject entered'
  if not 'message' in params or params['message'] == '':
    return 'No message entered'

  if not re.match(r'^\w[\w.+!-]+@\w[\w.-]+\.[a-zA-Z]{2,6}$', params['email']):
    return 'Invalid email address'

  sendMail(get_config().get('formmail', 'template'), params)
  return 'Message sent'
