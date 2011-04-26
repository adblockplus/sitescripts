# coding=utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

import cgi
from urlparse import parse_qsl
from openid.server.server import Server, ProtocolError, EncodingError
from openid.store.memstore import MemoryStore
from openid.extensions.sreg import SRegRequest, SRegResponse
from sitescripts.utils import get_config, setupStderr
from sitescripts.web import url_handler

openIDServer = Server(MemoryStore(), get_config().get('openid', 'serverUrl'))

@url_handler('/openid')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  params = {}
  if 'QUERY_STRING' in environ:
    for key, value in  parse_qsl(environ['QUERY_STRING']):
      params[key] = value

  if environ['REQUEST_METHOD'].upper() == 'POST' and environ.get('CONTENT_TYPE', 'application/x-www-form-urlencoded').startswith('application/x-www-form-urlencoded'):
    post_data = environ['wsgi.input'].read(environ.get('CONTENT_LENGTH', 0))
    for key, value in parse_qsl(post_data):
      params[key] = value

  try:
    request = openIDServer.decodeRequest(params)
  except ProtocolError, error:
    return displayResponse(error, start_response)

  if request is None:
    return showErrorPage('<p>Empty request</p>', start_response)

  if request.mode in ["checkid_immediate", "checkid_setup"]:
    is_authorized = environ['REMOTE_ADDR'] == environ['SERVER_ADDR']
    if is_authorized:
      response = request.answer(True)
      addSRegResponse(request, response)
    else:
      response = request.answer(False)
    return displayResponse(response, start_response)
  else:
    response = openIDServer.handleRequest(request)
    return displayResponse(response, start_response)

def addSRegResponse(request, response):
  user = get_config().get('openid', 'user')
  sreg_req = SRegRequest.fromOpenIDRequest(request)
  sreg_data = {'nickname': user, 'fullname': user}
  response.addExtension(SRegResponse.extractResponse(sreg_req, sreg_data))

def displayResponse(response, start_response):
  try:
    webresponse = openIDServer.encodeResponse(response)
  except EncodingError, error:
    return showErrorPage('<pre>%s</pre>' % cgi.escape(error.response.encodeToKVForm()), start_response)

  headers = []
  for header, value in webresponse.headers.iteritems():
    headers.append((header, value))
  start_response('%i OK' % webresponse.code, headers)
  return [webresponse.body]

def showErrorPage(message, start_response):
  start_response('400 Error Processing Request', [('Content-Type: ', 'text/html')])
  return [message]
