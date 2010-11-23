# coding=utf-8

import re, os, sys, codecs, subprocess, tarfile
from urlparse import urlparse
from StringIO import StringIO
from sitescripts.utils import get_config

def warn(message):
  print >> sys.stderr, message

class Subscription(object):
  def defineProperty(propName, isSimple = False):
    if isSimple:
      def setProperty(dict, propName, value):
        dict[propName] = value

      return property(lambda self: self._data[propName], lambda self, value: setProperty(self._data, propName, value))
    else:
      return property(lambda self: self._data[propName])

  name = defineProperty("name", True)
  type = defineProperty("type", True)
  maintainer = defineProperty("maintainer", True)
  email = defineProperty("email", True)
  specialization = defineProperty("specialization", True)
  languages = defineProperty("languages", True)
  recommendation = defineProperty("recommendation")
  deprecated = defineProperty("deprecated")
  unavailable = defineProperty("unavailable")
  catchall = defineProperty("catchall")
  supplements = defineProperty("supplements")
  supplemented = defineProperty("supplemented")
  variants = defineProperty("variants")
  homepage = defineProperty("homepage", True)
  contact = defineProperty("contact", True)
  forum = defineProperty("forum", True)
  faq = defineProperty("faq", True)
  blog = defineProperty("blog", True)
  changelog = defineProperty("changelog", True)
  digest = defineProperty("digest", True)

  def __init__(self, filePath, data):
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
      'supplemented': [],
      'variants': [],
      'recommendation': None,
      'homepage': None,
      'contact': None,
      'forum': None,
      'faq': None,
      'blog': None,
      'changelog': None,
      'digest': 'weekly',
    }
    self.parse(filePath, data)

  def parse(self, filePath, data):
    languages = {
      'ar': u'العربية',
      'bg': u'български',
      'cs': u'čeština',
      'da': u'dansk',
      'de': u'Deutsch',
      'en': u'English',
      'es': u'español',
      'fi': u'suomi',
      'fr': u'français',
      'gr': u'ελληνικά',
      'he': u'עברית',
      'hi': u'भारतीय',
      'hu': u'magyar',
      'id': u'Bahasa Indonesia',
      'is': u'íslenska',
      'it': u'italiano',
      'ja': u'日本語',
      'ko': u'한국어',
      'nl': u'Nederlands',
      'no': u'norsk',
      'pl': u'polski',
      'pt': u'português',
      'ro': u'românesc',
      'ru': u'русский',
      'sv': u'svensk',
      'ta': u'தமிழ்',
      'tr': u'Türkçe',
      'uk': u'українська',
      'vi': u'Việt',
      'zh': u'汉语',
    }
    mandatory = [['email'], ['specialization'], ['homepage', 'contact', 'forum', 'faq', 'blog']]

    self.name = re.sub(r'\.\w+$', r'', os.path.basename(filePath))

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

        oldValue = getattr(self, key)
        setattr(self, key, value)
        if value == '':
          warn('Empty value given for attribute %s in %s' % (key, filePath))
        if oldValue != None and key != 'name' and key != 'type' and key != 'digest':
          warn('Value for attribute %s is duplicated in %s' % (key, filePath))
      except:
        # Not a simple attribute, needs special handling
        if key == 'supplements':
          if value == '':
            warn('Empty value given for attribute %s in %s' % (key, filePath))
          self.supplements.append(value)

        elif key == 'list' or key == 'variant':
          if value == '':
            warn('Empty value given for attribute %s in %s' % (key, filePath))
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
                warn('Unknown keyword %s given for attribute %s in %s' % (keyword, key, filePath))
          (name, url) = (self.name, value)
          if key == 'variant':
            match = re.search(r'(.+?)\s+(\S+)$', value)
            if match:
              (name, url) = (match.group(1), match.group(2));
            else:
              warn('Invalid variant format in %s, no name given?' % (filePath))
          if not _validateURL(url):
            warn('Invalid list URL %s given in %s' % (url, filePath))
          self.variants.append([name, url, keywords['complete']])
          if keywords['recommendation']:
            self._data['recommendation'] = self._data['variants'][-1]
            self._data['catchall'] = keywords['catchall']

        elif key == 'deprecated' or key == 'unavailable':
          self._data[key] = True

        else:
          warn('Unknown attribute %s in %s' % (key, filePath))

      if key == 'languages':
        languageNames = []
        for language in value.split(','):
          if language in languages:
            languageNames.append(languages[language])
          else:
            warn('Unknown language code %s in %s' % (language, filePath))
        self._data['languageSpecialization'] = ', '.join(languageNames)

    if 'languageSpecialization' in self._data:
      if self.specialization != None:
        self.specialization +=  ", " + self._data['languageSpecialization']
      else:
        self.specialization = self._data['languageSpecialization']
      del self._data['languageSpecialization']

    for mandatorySet in mandatory:
      found = False
      for key in mandatorySet:
        if self._data[key] != None:
          found = True
      if not found:
        str = ", ".join(mandatorySet)
        warn('None of the attributes %s present in %s' % (str, filePath))

    if len(self.variants) == 0:
      warn('No list locations given in %s' % (filePath))
    if self.type != 'ads' and self.type != 'other':
      warn('Unknown type given in %s' % (filePath))
    if self.digest != 'daily' and self.digest != 'weekly':
      warn('Unknown digest frequency given in %s' % (filePath))
    if self.recommendation != None and (self.languages == None or not re.search(r'\S', self.languages)):
      warn('Recommendation without languages in %s' % (filePath))
    if len(self.supplements) == 0:
      for [name, url, complete] in self.variants:
        if complete:
          warn('Variant marked as complete for non-supplemental subscription in %s' % (filePath))
          break

    self.variants.sort(key=lambda variant: (self.recommendation == variant) * 2 + variant[2], reverse=True)

def parseFile(filePath, data):
  return Subscription(filePath, data)

def calculateSupplemented(lists):
  for fileData in lists.itervalues():
    for supplements in fileData.supplements:
      if supplements in lists:
        lists[supplements].supplemented.append(fileData)
      else:
        warn('Subscription %s supplements an unknown subscription %s' % (fileData.name, supplements))

def readSubscriptions():
  repo = os.path.abspath(get_config().get('subscriptions', 'repository'))
  (data, errors) = subprocess.Popen(['hg', 'archive', '-R', repo, '-r', 'default', '-t', 'tar', '-I', os.path.join(repo, '*.subscription'), '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors

  result =  {}
  tarFile = tarfile.open(mode='r:', fileobj=StringIO(data))
  fileInfo = tarFile.next()
  while fileInfo:
    fileData = parseFile(fileInfo.name, codecs.getreader('utf8')(tarFile.extractfile(fileInfo)))
    fileInfo = tarFile.next()
    if fileData.unavailable:
      continue

    if fileData.name in result:
      warn('Name %s is claimed by multiple files' % (fileData.name))
    result[fileData.name] = fileData
  tarFile.close()

  calculateSupplemented(result)
  return result

def getFallbackData():
  repo = os.path.abspath(get_config().get('subscriptions', 'repository'))
  (redirectData, errors) = subprocess.Popen(['hg', '-R', repo, 'cat', '-r', 'default', os.path.join(repo, 'redirects')], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors

  (goneData, errors) = subprocess.Popen(['hg', '-R', repo, 'cat', '-r', 'default', os.path.join(repo, 'gone')], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
  if errors:
    print >>sys.stderr, errors

  return (redirectData, goneData)

def _validateURL(url):
  parseResult = urlparse(url)
  return (parseResult.scheme == 'http' or parseResult.scheme == 'https') and parseResult.netloc != ''
