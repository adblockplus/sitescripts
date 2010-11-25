#!/usr/bin/python
# coding=utf-8

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

srv = WSGIServer(MultiplexerApp(), debug=False)

if __name__ == '__main__':
  srv.run()

