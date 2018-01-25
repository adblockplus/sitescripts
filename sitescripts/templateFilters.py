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

import re
import email.header
import email.utils
import urllib
import time
import json
from datetime import date
from jinja2.utils import Markup
from urlparse import urlparse


def formattime(value):
    try:
        return time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(int(value)))
    except Exception as e:
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
        title = unicode(title).replace('*', '<span class="censored">*</span>').replace(u'\u2026', u'<span class="censored">\u2026</span>')
        return Markup('<a href="%(url)s">%(title)s</a>' % {'url': url, 'title': title})
    else:
        return url


def formatnewlines(value):
    value = Markup.escape(value)
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


def formatBugLinks(value):
    def addLink(match):
        linkApp = match.group(1)
        if linkApp != None:
            linkApp = linkApp.lower()
        linkType = match.group(2).lower()
        linkNum = int(match.group(3))
        if linkType == 'topic':
            link = 'https://adblockplus.org/forum/viewtopic.php?t=%i' % linkNum
        elif linkApp == None and linkType == 'issue':
            link = 'https://issues.adblockplus.org/ticket/%i' % linkNum
        elif linkApp == 'webkit':
            link = 'https://bugs.webkit.org/show_bug.cgi?id=%i' % linkNum
        elif linkApp != None:
            link = 'http://code.google.com/p/chromium/issues/detail?id=%i' % linkNum
        else:
            link = 'https://bugzilla.mozilla.org/show_bug.cgi?id=%i' % linkNum
        return '<a href="%s">%s</a>' % (link, match.group(0))

    regexp = re.compile(r'(https?://\S+?)([.,:;!?"\']?(?:\s|$))', re.I | re.U)
    regexp2 = re.compile(r'(?:\b(WebKit|Chrome|Chromium)\s+)?\b(bug|issue|topic)\s+(\d+)', re.I | re.U)
    value = unicode(Markup.escape(value))
    value = re.sub(regexp, r'<a href="\1">\1</a>\2', value)
    value = re.sub(regexp2, addLink, value)
    return Markup(value)


def urlencode(value):
    return urllib.quote(value.encode('utf-8'), '')


def subscriptionSort(value, prioritizeRecommended=True):
    value = value[:]  # create a copy of the list
    if prioritizeRecommended:
        value.sort(
            lambda a, b:
                cmp(a.type, b.type) or
                cmp(a.deprecated, b.deprecated) or
                cmp(b.catchall, a.catchall) or
                cmp(b.recommendation != None, a.recommendation != None) or
                cmp(a.name.lower(), b.name.lower())
        )
    else:
        value.sort(
            lambda a, b:
                cmp(a.type, b.type) or
                cmp(a.deprecated, b.deprecated) or
                cmp(a.name.lower(), b.name.lower())
        )
    return value


def formatmime(text):
    # See http://bugs.python.org/issue5871 (not really fixed), Header() will
    # happily accept non-printable characters including newlines. Make sure to
    # remove them.
    text = re.sub(r'[\x00-\x1F]', '', text)
    return email.header.Header(text).encode()


def ljust(value, width=80):
    return unicode(value).ljust(width)


def rjust(value, width=80):
    return unicode(value).rjust(width)


def ltruncate(value, length=255, end='...'):
    value = unicode(value)
    if len(value) <= length:
        return value
    return end + value[len(value) - length:len(value)]


def formatweekday(value):
    return time.strftime('%a', (0, 0, 0, 0, 0, 0, value, 0, 0))


def formatbytes(value):
    if value == 0:
        return '0'

    value = float(value)
    unit = 'Bytes'
    if value > 1024:
        value /= 1024
        unit = 'KB'
    if value > 1024:
        value /= 1024
        unit = 'MB'
    if value > 1024:
        value /= 1024
        unit = 'GB'
    return '%.2f %s' % (value, unit)


def toJSON(value, **args):
    return re.sub(r'</script>', r'<\/script>', json.dumps(value, **args))


filters = {
    'formattime': formattime,
    'timerelative': formatrelativetime,
    'url': formaturl,
    'keepnewlines': formatnewlines,
    'filtercount': formatfiltercount,
    'buglinks': formatBugLinks,
    'urlencode': urlencode,
    'subscriptionSort': subscriptionSort,
    'mime': formatmime,
    'emailaddr': email.utils.formataddr,
    'ljust': ljust,
    'rjust': rjust,
    'ltruncate': ltruncate,
    'weekday': formatweekday,
    'bytes': formatbytes,
    'json': toJSON,
}
