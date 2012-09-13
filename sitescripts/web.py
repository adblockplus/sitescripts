# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import base64
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

def basic_auth(f):
  return lambda environ, start_response: authenticate(f, environ, start_response)

def authenticate(f, environ, start_response):
  if "HTTP_AUTHORIZATION" in environ:
    auth = environ["HTTP_AUTHORIZATION"].split()
    if len(auth) == 2:
      if auth[0].lower() == "basic":
        username, password = base64.b64decode(auth[1]).split(":")
        expected_username = get_config().get("DEFAULT", "basic_auth_username")
        expected_password = get_config().get("DEFAULT", "basic_auth_password")
        if username == expected_username and password == expected_password:
          return f(environ, start_response)

  realm = get_config().get("DEFAULT", "basic_auth_realm")
  start_response("401 UNAUTHORIZED",
                 [("WWW-Authenticate", 'Basic realm="%s"' % realm)])
  return ""

import openid.web.server
import subscriptions.web.fallback
import reports.web.submitReport
import reports.web.updateReport
import reports.web.showDigest
import extensions.web.translationCheck
import tasks.web.tasks
import formmail.web.formmail
import crawler.web.crawler
