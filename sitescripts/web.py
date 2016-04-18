# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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

import base64
import imp
import importlib
import re
import httplib
import urllib
from urlparse import parse_qsl

from sitescripts.utils import get_config

handlers = {}
authenticated_users = {}


def url_handler(url):
    def decorator(func):
        registerUrlHandler(url, func)
        return func
    return decorator


def registerUrlHandler(url, func):
    if url in handlers:
        raise Exception('A handler for url %s is already registered' % url)
    handlers[url] = func

# https://www.python.org/dev/peps/pep-0333/#url-reconstruction


def request_path(environ, include_query=True):
    path = urllib.quote(environ.get("SCRIPT_NAME", "") +
                        environ.get("PATH_INFO", ""))
    query_string = environ.get("QUERY_STRING", "")
    if query_string and include_query:
        path += "?" + urllib.quote(query_string)
    return path


def basic_auth(config_section="DEFAULT"):
    def decorator(function):
        def authenticating_wrapper(environ, start_response):
            return authenticate(function, environ, start_response, config_section)
        return authenticating_wrapper
    return decorator


def authenticate(f, environ, start_response, config_section):
    if "HTTP_AUTHORIZATION" in environ:
        auth = environ["HTTP_AUTHORIZATION"].split()
        if len(auth) == 2:
            if auth[0].lower() == "basic":
                username, password = base64.b64decode(auth[1]).split(":")
                config = get_config()
                expected_username = config.get(config_section, "basic_auth_username")
                expected_password = config.get(config_section, "basic_auth_password")
                if username == expected_username and password == expected_password:
                    return f(environ, start_response)

    realm = get_config().get("DEFAULT", "basic_auth_realm")
    start_response("401 UNAUTHORIZED",
                   [("WWW-Authenticate", 'Basic realm="%s"' % realm)])
    return ""


def send_simple_response(start_response, status_code, text=None):
    status_text = httplib.responses[status_code]

    status = '%d %s' % (status_code, status_text)
    start_response(status, [('Content-Type', 'text/plain')])

    if text is not None:
        return [text]
    return [status_text]


def form_handler(func):
    def wrapper(environ, start_response):
        if environ['REQUEST_METHOD'] != 'POST':
            return send_simple_response(start_response, 405)

        if not environ.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
            return send_simple_response(start_response, 415)

        try:
            content_length = int(environ['CONTENT_LENGTH'])
        except (KeyError, ValueError):
            content_length = None
        if content_length is None or content_length < 0:
            return send_simple_response(start_response, 411)

        raw_data = parse_qsl(environ['wsgi.input'].read(content_length))
        try:
            data = {k.decode('utf-8'): v.decode('utf-8') for k, v in raw_data}
        except UnicodeDecodeError:
            return send_simple_response(start_response, 400, 'Invalid form data encoding')

        return func(environ, start_response, data)

    return wrapper


def multiplex(environ, start_response):
    try:
        path = environ["PATH_INFO"]
        try:
            handler = handlers[path]
        except KeyError:
            handler = handlers[re.sub(r"[^/]+$", "", path)]
    except KeyError:
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return ["Not Found"]

    return handler(environ, start_response)

for module in set(get_config().options("multiplexer")) - set(get_config().defaults()):
    module_path = get_config().get("multiplexer", module)
    if module_path:
        imp.load_source(module, module_path)
    else:
        importlib.import_module(module)
