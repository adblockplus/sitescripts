from flask import Flask, request
from sitescripts.web import handlers
from urlparse import urlparse

app = Flask(__name__)

@app.route('/<path:path>')
def multiplex(path):
  request_url = urlparse(request.url)
  print request_url.query
  request_path = request_url.path
  if request_path in handlers:
    # TODO: Some more environ entries are required for all scripts to work.
    environ = {'QUERY_STRING': request_url.query}
    # TODO: Actually return the supplied status/headers.
    start_response = lambda status, headers: None
    return handlers[request_path](environ, start_response)
  return ''

if __name__ == '__main__':
  app.run(debug=True)
