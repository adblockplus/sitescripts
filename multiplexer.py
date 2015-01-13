#!/usr/bin/env python
# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
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

import re
import flask
from sitescripts.web import handlers
from urlparse import urlparse

app = flask.Flask(__name__)

@app.route("/<path:path>", methods = ["GET", "POST"])
def multiplex(path):
  request_url = urlparse(flask.request.url)
  if 'SERVER_ADDR' not in flask.request.environ:
    flask.request.environ['SERVER_ADDR'] = flask.request.environ['SERVER_NAME']
  if 'REQUEST_URI' not in flask.request.environ:
    flask.request.environ['REQUEST_URI'] = flask.request.url

  request_path = request_url.path
  if request_path in handlers:
    return handlers[request_path]
  request_dir = re.sub(r'[^/]+$', '', request_path)
  if request_dir in handlers:
    return handlers[request_dir]
  return flask.abort(404)

if __name__ == "__main__":
  app.run(debug=True)
