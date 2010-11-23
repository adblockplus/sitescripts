#!/usr/bin/python
# coding=utf-8

from flup.server.fcgi import WSGIServer
from urlparse import urlparse

from sitescripts.subscriptions.web.fallback import handleSubscriptionFallbackRequest
from sitescripts.openid.web.server import handleOpenIDRequest
from sitescripts.reports.web.submitReport import handleReportRequest
from sitescripts.reports.web.updateReport import handleReportUpdateRequest

class MultiplexerApp:
  def __call__(self, environ, start_response):
    if 'REQUEST_URI' in environ:
      request = urlparse(environ['REQUEST_URI'])
      if request.path == '/getSubscription':
        return handleSubscriptionFallbackRequest(environ, start_response)
      elif request.path == '/submitReport':
        return handleReportRequest(environ, start_response)
      elif request.path == '/updateReport':
        return handleReportUpdateRequest(environ, start_response)
      elif request.path == '/openid':
        return handleOpenIDRequest(environ, start_response)

    start_response('404 Not Found', [('Content-Type', 'text/html')])
    return ["Not Found"]

srv = WSGIServer(MultiplexerApp(), debug=False)

if __name__ == '__main__':
  srv.run()

