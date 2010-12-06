# coding: utf-8

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
import abp.web.translationCheck
