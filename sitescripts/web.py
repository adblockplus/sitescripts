# coding: utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

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
import extensions.web.translationCheck
import tasks.web.tasks
import formmail.web.formmail
