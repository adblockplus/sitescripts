#!/usr/bin/python
# coding=utf-8

import os, re
from flup.server.fcgi import WSGIServer
from urlparse import urlparse

from sitescripts.web import handlers

class MultiplexerApp:
  def __call__(self, environ, start_response):
    if 'REQUEST_URI' in environ:
      request = urlparse(environ['REQUEST_URI'])
      if request.path in handlers:
        return handlers[request.path](environ, start_response)

    start_response('404 Not Found', [('Content-Type', 'text/html')])
    return ["Not Found"]

bindAddress = None
if 'FCGI_BIND_ADDRESS' in os.environ:
  match = re.match(r'^(.*?):(\d+)$', os.environ['FCGI_BIND_ADDRESS'])
  bindAddress = (match.group(1), int(match.group(2)))
srv = WSGIServer(MultiplexerApp(), debug=False, bindAddress=bindAddress)

if __name__ == '__main__':
  srv.run()

