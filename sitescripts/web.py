# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

handlers = {}

def url_handler(url):
  def decorator(func):
    registerUrlHandler(url, func)
    return func
  return decorator

def registerUrlHandler(url, func):
  if url in handlers:
    raise Exception('A handler for url %s is already registered' % url)
  handlers[url] = func

import openid.web.server
import subscriptions.web.fallback
import reports.web.submitReport
import reports.web.updateReport
import reports.web.showDigest
import extensions.web.translationCheck
import tasks.web.tasks
import formmail.web.formmail
