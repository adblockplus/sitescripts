#!/usr/bin/env python
# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import flask
from sitescripts.web import handlers
from urlparse import urlparse

app = flask.Flask(__name__)

@app.route("/<path:path>", methods = ["GET", "POST"])
def multiplex(path):
  request_url = urlparse(flask.request.url)
  request_path = request_url.path
  if request_path in handlers:
    if 'SERVER_ADDR' not in flask.request.environ:
      flask.request.environ['SERVER_ADDR'] = flask.request.environ['SERVER_NAME']
    return handlers[request_path]
  return flask.abort(404)

if __name__ == "__main__":
  app.run(debug=True)
