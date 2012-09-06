from flask import Flask, request
from sitescripts.web import handlers
from urlparse import urlparse

app = Flask(__name__)

@app.route('/<path:path>')
def multiplex(path):
  requestUrl = urlparse(request.url)
  print requestUrl.query
  requestPath = requestUrl.path
  if requestPath in handlers:
    # TODO: Some more environ entries are required for all scripts to work.
    environ = {'QUERY_STRING': requestUrl.query}
    # TODO: Actually return the supplied status/headers.
    start_response = lambda status, headers: None
    return handlers[requestPath](environ, start_response)
  return ''

if __name__ == '__main__':
  app.run(debug=True)
