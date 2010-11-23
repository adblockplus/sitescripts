# coding: utf-8

import email.header, urllib
from time import gmtime, strftime
from jinja2.utils import Markup
from urlparse import urlparse

def formattime(value):
  try:
    return strftime('%Y-%m-%d %H:%M GMT', gmtime(int(value)))
  except Exception, e:
    return 'unknown'

def formatrelativetime(value, baseTime):
  try:
    value = float(value)
    params = {'title': formattime(baseTime + value), 'number': value, 'prefix': 'in ', 'suffix': '', 'unit': 'second(s)'}
    if params['number'] < 0:
      params['prefix'] = ''
      params['suffix'] = ' ago'
      params['number'] = -params['number']
    if params['number'] >= 180:
      params['unit'] = 'minutes'
      params['number'] /= 60
      if params['number'] >= 180:
        params['unit'] = 'hours'
        params['number'] /= 60
        if params['number'] >= 72:
          params['unit'] = 'days'
          params['number'] /= 24
          if params['number'] >= 21:
            params['unit'] = 'weeks'
            params['number'] /= 7
    return Markup('<span title="%(title)s">%(prefix)s%(number)i %(unit)s%(suffix)s</span>' % params)
  except Exception:
    return 'unknown'

def formaturl(url, title=None):
  if not url:
    return ''

  if title is None:
    title = url
  parsed = urlparse(url)
  if parsed.scheme == 'http' or parsed.scheme == 'https':
    url = Markup.escape(url)
    title = Markup.escape(title)
    title = unicode(title).replace('*', '<span class="censored">*</span>').replace(u'…', u'<span class="censored">…</span>')
    return Markup('<a href="%(url)s">%(title)s</a>' % {'url': url, 'title': title})
  else:
    return url

def formatnewlines(value):
  value = Markup.escape(value);
  value = unicode(value).replace('\n', '<br />')
  return Markup(value)

def formatfiltercount(value):
  try:
    value = int(value)
    if value > 0:
      return 'yes, %i filter(s)' % value
    else:
      return 'none'
  except Exception:
    return 'unknown'

def urlencode(value):
  return urllib.quote(value.encode('utf-8'), '')

def subscriptionSort(value, prioritizeRecommended=True):
  value = value[:]  # create a copy of the list
  if prioritizeRecommended:
    value.sort(lambda a, b: (
      cmp(a.type, b.type) or
      cmp(a.deprecated, b.deprecated) or
      cmp(b.catchall, a.catchall) or
      cmp(b.recommendation != None, a.recommendation != None) or
      cmp(a.name.lower(), b.name.lower())
    ))
  else:
    value.sort(lambda a, b: (
      cmp(a.type, b.type) or
      cmp(a.deprecated, b.deprecated) or
      cmp(a.name.lower(), b.name.lower())
    ))
  return value

def formatmime(text):
  return email.header.Header(text).encode()

def ljust(value, width=80):
  return unicode(value).ljust(width)

def rjust(value, width=80):
  return unicode(value).rjust(width)

def ltruncate(value, length=255, end='...'):
  if len(value) <= length:
    return value
  return end + value[len(value) - length:len(value)]

filters = {
  'formattime': formattime,
  'timerelative': formatrelativetime,
  'url': formaturl,
  'keepnewlines': formatnewlines,
  'filtercount': formatfiltercount,
  'urlencode': urlencode,
  'subscriptionSort': subscriptionSort,
  'mime': formatmime,
  'ljust': ljust,
  'rjust': rjust,
  'ltruncate': ltruncate,
}
