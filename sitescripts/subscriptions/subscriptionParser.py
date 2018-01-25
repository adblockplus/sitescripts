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
import os
import sys
import codecs
import subprocess
import tarfile
from urlparse import urlparse
from StringIO import StringIO
from ConfigParser import SafeConfigParser
from sitescripts.utils import get_config, cached


def warn(message):
    print >> sys.stderr, message


class Subscription(object):
    def define_property(propName, readonly=False):
        if readonly:
            return property(lambda self: self._data[propName])
        else:
            def set_property(self, value):
                self._data[propName] = value

            return property(lambda self: self._data[propName], set_property)

    name = define_property('name')
    type = define_property('type')
    maintainer = define_property('maintainer')
    email = define_property('email')
    specialization = define_property('specialization')
    languages = define_property('languages')
    recommendation = define_property('recommendation', readonly=True)
    deprecated = define_property('deprecated', readonly=True)
    unavailable = define_property('unavailable', readonly=True)
    catchall = define_property('catchall', readonly=True)
    supplements = define_property('supplements', readonly=True)
    supplementsType = define_property('supplementsType', readonly=True)
    supplemented = define_property('supplemented', readonly=True)
    variants = define_property('variants', readonly=True)
    homepage = define_property('homepage')
    contact = define_property('contact')
    forum = define_property('forum')
    faq = define_property('faq')
    blog = define_property('blog')
    changelog = define_property('changelog')
    policy = define_property('policy')
    digest = define_property('digest')
    digestDay = define_property('digestDay')

    def __init__(self, path, data):
        self._data = {
            'name': None,
            'type': 'ads',
            'maintainer': None,
            'email': None,
            'specialization': None,
            'languages': None,
            'deprecated': False,
            'unavailable': False,
            'catchall': False,
            'supplements': [],
            'supplementsType': set(),
            'supplemented': [],
            'variants': [],
            'recommendation': None,
            'homepage': None,
            'contact': None,
            'forum': None,
            'faq': None,
            'blog': None,
            'changelog': None,
            'policy': None,
            'digest': 'weekly',
            'digestDay': 'wed',
        }
        self.parse(path, data)

    def parse(self, path, data):
        mandatory = [['email'], ['specialization'], ['homepage', 'contact', 'forum', 'faq', 'blog']]
        weekdays = {
            'son': 0,
            'mon': 1,
            'tue': 2,
            'wed': 3,
            'thu': 4,
            'fri': 5,
            'sat': 6,
        }

        self.name = re.sub(r'\.\w+$', r'', os.path.basename(path))

        for line in data:
            if not re.search(r'\S', line):
                continue

            parts = line.split('=', 1)
            key = parts[0].strip()
            if len(parts) > 1:
                value = parts[1].strip()
            else:
                value = ''

            try:
                # Might be a simple attribute - try setting the value
                if not hasattr(self, key):
                    raise Exception()

                oldvalue = getattr(self, key)
                setattr(self, key, value)
                if value == '':
                    warn('Empty value given for attribute %s in %s' % (key, path))
                if oldvalue != None and key != 'name' and key != 'type' and key != 'digest' and key != 'digestDay':
                    warn('Value for attribute %s is duplicated in %s' % (key, path))
            except:
                # Not a simple attribute, needs special handling
                if key == 'supplements':
                    if value == '':
                        warn('Empty value given for attribute %s in %s' % (key, path))
                    self.supplements.append(value)

                elif key == 'list' or key == 'variant':
                    if value == '':
                        warn('Empty value given for attribute %s in %s' % (key, path))
                    keywords = {
                        'recommendation': False,
                        'catchall': False,
                        'complete': False,
                    }
                    regexp = re.compile(r'\s*\[((?:\w+,)*\w+)\]$')
                    match = re.search(regexp, value)
                    if match:
                        value = re.sub(regexp, r'', value)
                        for keyword in match.group(1).split(','):
                            keyword = keyword.lower()
                            if keyword in keywords:
                                keywords[keyword] = True
                            else:
                                warn('Unknown keyword %s given for attribute %s in %s' % (keyword, key, path))
                    name, url = self.name, value
                    if key == 'variant':
                        match = re.search(r'(.+?)\s+(\S+)$', value)
                        if match:
                            name, url = match.group(1), match.group(2)
                        else:
                            warn('Invalid variant format in %s, no name given?' % path)
                    if not _validate_URL(url):
                        warn('Invalid list URL %s given in %s' % (url, path))
                    self.variants.append([name, url, keywords['complete']])
                    if keywords['recommendation']:
                        self._data['recommendation'] = self._data['variants'][-1]
                        self._data['catchall'] = keywords['catchall']

                elif key == 'deprecated' or key == 'unavailable':
                    self._data[key] = True

                else:
                    warn('Unknown attribute %s in %s' % (key, path))

            if key == 'languages':
                settings = get_settings()
                languagenames = []
                for language in value.split(','):
                    if settings.has_option('languages', language):
                        languagenames.append(settings.get('languages', language))
                    else:
                        warn('Unknown language code %s in %s' % (language, path))
                self._data['languageSpecialization'] = ', '.join(languagenames)

        if 'languageSpecialization' in self._data:
            if self.specialization != None:
                self.specialization += ', ' + self._data['languageSpecialization']
            else:
                self.specialization = self._data['languageSpecialization']
            del self._data['languageSpecialization']

        for group in mandatory:
            found = False
            for key in group:
                if self._data[key] != None:
                    found = True
            if not found:
                str = ', '.join(group)
                warn('None of the attributes %s present in %s' % (str, path))

        if len(self.variants) == 0:
            warn('No list locations given in %s' % path)
        if self.type not in ('ads', 'anti-adblock', 'other', 'malware', 'social', 'privacy'):
            warn('Unknown type given in %s' % path)
        if self.digest != 'daily' and self.digest != 'weekly':
            warn('Unknown digest frequency given in %s' % path)
        if not self.digestDay[0:3].lower() in weekdays:
            warn('Unknown digest day given in %s' % path)
            self.digestDay = 'wed'
        self.digestDay = weekdays[self.digestDay[0:3].lower()]
        if self.recommendation is not None and self.type == 'ads' and not (self.languages and self.languages.strip()):
            warn('Recommendation without languages in %s' % path)
        if len(self.supplements) == 0:
            for [name, url, complete] in self.variants:
                if complete:
                    warn('Variant marked as complete for non-supplemental subscription in %s' % path)
                    break

        self.variants.sort(key=lambda variant: (self.recommendation == variant) * 2 + variant[2], reverse=True)


def parse_file(path, data):
    return Subscription(path, data)


def calculate_supplemented(lists):
    for filedata in lists.itervalues():
        for supplements in filedata.supplements:
            if supplements in lists:
                if lists[supplements].type == filedata.type:
                    lists[supplements].supplemented.append(filedata)
                filedata.supplementsType.add(lists[supplements].type)
            else:
                warn('Subscription %s supplements an unknown subscription %s' % (filedata.name, supplements))


@cached(60)
def get_settings():
    repo = os.path.abspath(get_config().get('subscriptions', 'repository'))
    settingsdata = subprocess.check_output(['hg', '-R', repo, 'cat', '-r', 'default', os.path.join(repo, 'settings')])
    settings = SafeConfigParser()
    settings.readfp(codecs.getreader('utf8')(StringIO(settingsdata)))
    return settings


def readSubscriptions():
    repo = os.path.abspath(get_config().get('subscriptions', 'repository'))
    data = subprocess.check_output(['hg', 'archive', '-R', repo, '-r', 'default', '-t', 'tar', '-I', os.path.join(repo, '*.subscription'), '-'])

    result = {}
    with tarfile.open(mode='r:', fileobj=StringIO(data)) as archive:
        for fileinfo in archive:
            filedata = parse_file(fileinfo.name, codecs.getreader('utf8')(archive.extractfile(fileinfo)))
            if filedata.unavailable:
                continue

            if filedata.name in result:
                warn('Name %s is claimed by multiple files' % filedata.name)
            result[filedata.name] = filedata

    calculate_supplemented(result)
    return result


def getFallbackData():
    repo = os.path.abspath(get_config().get('subscriptions', 'repository'))
    redirectdata = subprocess.check_output(['hg', '-R', repo, 'cat', '-r', 'default', os.path.join(repo, 'redirects')])
    gonedata = subprocess.check_output(['hg', '-R', repo, 'cat', '-r', 'default', os.path.join(repo, 'gone')])
    return (redirectdata, gonedata)


def _validate_URL(url):
    parse_result = urlparse(url)
    return parse_result.scheme in ('http', 'https') and parse_result.netloc != ''
