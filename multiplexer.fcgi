#!/usr/bin/env python
# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2014 Eyeo GmbH
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

