# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-present eyeo GmbH
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

import json
import re
from urlparse import parse_qs

from wsgiref.simple_server import make_server

_AUTH_RESPONSE = {
    'access_token': '1/8xbJqaOZXSUZbHLl5EOtu1pxz3fmmetKx9W8CV4t79M',
    'token_type': 'Bearer',
    'expires_in': 3600,
}

_NOT_FOUND_RESPONSE = {
    'error': {
        'errors': [{
            'domain': 'global',
            'reason': 'notFound',
            'message': 'File not found: {}',
            'locationType': 'parameter',
            'location': 'fileId',
        }],
        'code': '404',
        'message': 'File not found: {}',
    },
}


def download(environ, start_response):
    """Send a file from a given path to the client."""
    d = parse_qs(environ['QUERY_STRING'])
    path = d.get('path')
    headers = list()
    try:
        file = open(path[0], 'rb')
        start_response('200 OK', headers)
        if 'wsgi.file_wrapper' in environ:
            return environ['wsgi.file_wrapper'](file, 1024)

        return iter(lambda: file.read(1024), '')
    except IOError:
        response = _NOT_FOUND_RESPONSE
        response['error']['errors'][0]['message'] = \
            response['error']['errors'][0]['message'].format(path)
        response['error']['message'] = \
            response['error']['message'].format(path)

        headers = [('content-type', 'text/plain')]
        start_response('404 NOT FOUND', headers)
        return [json.dumps(response, encoding='utf-8')]


def auth(environ, start_response):
    """Simulate a successful authentication using Google Oauth2."""
    headers = [('content-type', 'application/json')]
    response = json.dumps(_AUTH_RESPONSE, encoding='utf-8')

    start_response('200 OK', headers)

    return [response]


_URLS = [
    (r'oauth2/v4/token/?$', auth),
    (r'download/?$', download),
]


def main(environ, start_response):
    """Serve as ain entry point for the dummy google API."""
    path = environ.get('PATH_INFO', '').lstrip('/')
    for regex, callback in _URLS:
        match = re.search(regex, path)
        if match is not None:
            environ['myapp.url_args'] = match.groups()
            return callback(environ, start_response)


if __name__ == '__main__':
    app = make_server('localhost', 8080, main)
    app.serve_forever()
