# coding: utf-8

import os, sys, re, marshal, codecs
from urlparse import urlparse
from time import time
from xml.parsers.expat import ParserCreate, ExpatError, ErrorString
from sitescripts.utils import get_config, setupStderr
from sitescripts.reports.utils import saveReport
import sitescripts.subscriptions.knownIssuesParser as knownIssuesParser

reportData = None
tagStack = None

lengthRestrictions = {
  'default_string': 1024,
  'default_list': 512,
  'abp_version': 32,
  'abp_build': 32,
  'abp_locale': 32,
  'app_name': 32,
  'app_vendor': 32,
  'app_version': 32,
  'platform_name': 32,
  'platform_version': 32,
  'platform_build': 32,
  'requests.type': 32,
  'requests.size': 32,
  'filters.hitCount': 16,
  'subscriptions.lastDownloadAttempt': 16,
  'subscriptions.lastDownloadSuccess': 16,
  'subscriptions.softExpiration': 16,
  'subscriptions.hardExpiration': 16,
  'subscriptions.downloadStatus': 32,
  'errors': 16,
  'errors.type': 16,
  'errors.line': 16,
  'errors.column': 16,
  'extensions.version': 32,
  'extensions.type': 32,
  'email': 256,
  'screenshot': 1024*1024,
}

def scanReports(dir):
  for file in os.listdir(dir):
    filePath = os.path.join(dir, file)
    if os.path.isdir(filePath):
      scanReports(filePath)
    elif os.stat(filePath).st_mtime < time() - 30*24*60*60:
      # Remove files that are older than 30 days
      os.remove(filePath)
    elif file.endswith('.xml'):
      dumpFile = re.sub(r'\.xml$', '.dump', filePath)
      htmlFile = re.sub(r'\.xml$', '.html', filePath)
      if os.path.exists(dumpFile) or os.path.exists(htmlFile):
        continue
      processReport(filePath, dumpFile, htmlFile)

def processReport(xmlFile, dumpFile, htmlFile):
  global reportData, tagStack

  source = open(xmlFile, 'rb')
  target = open(dumpFile, 'wb')
  reportData = {'status': '',  'warnings': {}, 'requests': [], 'filters': [], 'subscriptions': [], 'extensions': [], 'errors': [], 'time': time()}
  tagStack = []

  parser = ParserCreate()
  parser.StartElementHandler = processElementStart
  parser.EndElementHandler = processElementEnd
  parser.CharacterDataHandler = processText
  try:
    parser.ParseFile(source)
  except ExpatError, error:
    reportData['warnings']['!parsing'] = 'Parsing error in the report: %s at line %i column %i' % (ErrorString(error.code), error.lineno, error.offset)

  source.seek(0)
  reportData['knownIssues'] = knownIssuesParser.findMatches(source, 'en-US')
  source.close()

  if 'screenshot' in reportData and not reportData['screenshot'].startswith('data:image/'):
    del reportData['screenshot']
  validateData(reportData)

  marshal.dump(reportData, target)
  target.close()

  saveReport(reportData, htmlFile)

  if not len(reportData['warnings']):
    os.remove(xmlFile)

def processElementStart(name, attributes):
  global reportData, tagStack

  if name == 'report':
    reportData['type'] = attributes.get('type', 'unknown')
  elif name == 'adblock-plus':
    reportData['abp_version'] = attributes.get('version', 'unknown')
    if reportData['abp_version'] == '99.9':
      reportData['abp_version'] = 'development environment'
    reportData['abp_build'] = attributes.get('build', 'unknown')
    if reportData['abp_build'] == '':
      reportData['abp_build'] = 'unknown'
    reportData['abp_locale'] = attributes.get('locale', 'unknown')
  elif name == 'application':
    reportData['app_name'] = attributes.get('name', 'unknown')
    reportData['app_vendor'] = attributes.get('vendor', 'unknown')
    reportData['app_version'] = attributes.get('version', 'unknown')
    reportData['app_ua'] = attributes.get('userAgent', 'unknown')
  elif name == 'platform':
    reportData['platform_name'] = attributes.get('name', 'unknown')
    reportData['platform_version'] = attributes.get('version', 'unknown')
    reportData['platform_build'] = attributes.get('build', 'unknown')
  elif name == 'window':
    reportData['main_url'] = attributes.get('url', 'unknown')
    parsed = urlparse(reportData['main_url'])
    if parsed.netloc:
      reportData['siteName'] = parsed.netloc
    else:
      reportData['siteName'] = 'unknown'

    reportData['opener'] = attributes.get('opener', '')
    parsed = urlparse(reportData['opener'])
    if parsed.netloc:
      reportData['openerSite'] = parsed.netloc
    else:
      reportData['openerSite'] = 'unknown'
  elif name == 'request':
    reportData['requests'].append({\
          'location': attributes.get('location', ''),\
          'type': attributes.get('type', 'unknown'),\
          'docDomain': attributes.get('docDomain', 'unknown'),\
          'thirdParty': (attributes.get('thirdParty', 'false') == 'true'),\
          'size': attributes.get('size', ''),\
          'filter': attributes.get('filter', ''),\
    })
  elif name == 'filter':
    reportData['filters'].append({\
          'text': attributes.get('text', 'unknown'),\
          'subscriptions': map(translateSubscriptionName, attributes.get('subscriptions', 'unknown').split(' ')),\
          'hitCount': attributes.get('hitCount', 'unknown'),\
    })
  elif name == 'subscription':
    reportData['subscriptions'].append({\
          'id': attributes.get('id', 'unknown'),\
          'disabledFilters': attributes.get('disabledFilters', 'unknown'),\
          'lastDownloadAttempt': attributes.get('lastDownloadAttempt', 'unknown'),\
          'lastDownloadSuccess': attributes.get('lastDownloadSuccess', 'unknown'),\
          'softExpiration': attributes.get('softExpiration', 'unknown'),\
          'hardExpiration': attributes.get('hardExpiration', 'unknown'),\
          'autoDownloadEnabled': (attributes.get('autoDownloadEnabled', 'false') == 'true'),\
          'downloadStatus': attributes.get('downloadStatus', 'unknown'),\
    })
  elif name == 'extension':
    reportData['extensions'].append({\
          'id': attributes.get('id', 'unknown'),\
          'name': attributes.get('name', 'unknown'),\
          'version': attributes.get('version', 'unknown'),\
          'type': attributes.get('type', 'unknown'),\
    })
  elif name == 'error':
    reportData['errors'].append({\
          'type': attributes.get('type', 'unknown'),\
          'text': attributes.get('text', 'unknown'),\
          'file': attributes.get('file', 'unknown'),\
          'line': attributes.get('line', 'unknown'),\
          'column': attributes.get('column', 'unknown'),\
          'sourceLine': re.sub(r'[\r\n]+$', '', attributes.get('sourceLine', '')),\
    })

  tagStack.append([name, attributes])

def processElementEnd(name):
  global tagStack
  tagStack.pop()

def processText(text):
  if not len(tagStack):
    return

  [name, attributes] = tagStack[-1];
  if name == 'option':
    if attributes.get('id', None) == 'enabled':
      reportData['option_enabled'] = (text == 'true')
    if attributes.get('id', None) == 'objecttabs':
      reportData['option_objecttabs'] = (text == 'true')
    elif attributes.get('id', None) == 'collapse':
      reportData['option_collapse'] = (text == 'true')
    elif attributes.get('id', None) == 'privateBrowsing':
      reportData['option_privateBrowsing'] = (text == 'true')
  elif name == 'screenshot':
    if 'screenshot' in reportData:
      reportData['screenshot'] += text
    else:
      reportData['screenshot'] = text
  elif name == 'comment':
    if 'comment' in reportData:
      reportData['comment'] += text
    else:
      reportData['comment'] = text
  elif name == 'email':
    if 'email' in reportData:
      reportData['email'] += text
    else:
      reportData['email'] = text

def translateSubscriptionName(name):
  if name == '~fl~':
    return 'My Ad Blocking Rules'
  elif name == '~wl~':
    return 'My Exception Rules'
  elif name == '~eh~':
    return 'My Element Hiding Rules'
  elif name == '~il~':
    return 'My Invalid Rules'
  elif name.startswith('~external~'):
    return 'External: ' + name[len('~external~'):len(name)]
  else:
    return name

def validateData(data, path=None):
  if path == 'warnings':
    return

  for key in data:
    if path is None:
      keyPath = key
    else:
      keyPath = path + '.' + key

    if isinstance(data[key], dict):
      validateData(data[key], keyPath)
    elif isinstance(data[key], list):
      limit = lengthRestrictions.get(keyPath, lengthRestrictions['default_list'])
      if len(data[key]) > limit:
        data[key] = data[key][0:limit]
        reportData['warnings'][keyPath] = 'List %s exceeded length limit and was truncated' % keyPath
      for i in range(len(data[key])):
        if isinstance(data[key][i], dict):
          validateData(data[key][i], keyPath)
        elif isinstance(data[key][i], basestring):
          itemPath = keyPath + '.item'
          limit = lengthRestrictions.get(itemPath, lengthRestrictions['default_string'])
          if len(data[key][i]) > limit:
            data[key][i] = data[key][i][0:limit] + u'…'
            reportData['warnings'][itemPath] = 'Field %s exceeded length limit and was truncated' % itemPath
    elif isinstance(data[key], basestring):
      limit = lengthRestrictions.get(keyPath, lengthRestrictions['default_string'])
      if len(data[key]) > limit:
        data[key] = data[key][0:limit] + u'…'
        reportData['warnings'][keyPath] = 'Field %s exceeded length limit and was truncated' % keyPath

if __name__ == '__main__':
  setupStderr()
  scanReports(get_config().get('reports', 'dataPath'))
