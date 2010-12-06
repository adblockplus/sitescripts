# coding: utf-8

import urllib, urllib2, cookielib, re, string, tempfile, os, subprocess, tarfile, shutil
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
from sitescripts.utils import get_config, get_template, setupStderr, cached
from sitescripts.web import url_handler
from urlparse import parse_qs

class BabelzillaConnection:
  def __init__(self, user, password):
    cj = cookielib.CookieJar()
    self.url_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    try:
      self.openurl('http://www.babelzilla.org/index.php', \
                   {'username': user, 'passwd': password, 'option': 'ipblogin', 'task':'login'})
      if not any(cookie.name == 'bbmember_id' for cookie in cj):
        raise Exception('Server didn\'t log us in')
    except Exception, e:
      raise Exception('Babelzilla login failed. %s', str(e))

  def statusLine(code):
    msg = BaseHTTPRequestHandler.responses.get(code, ['unknown', 'unknown'])
    return 'Code %i (%s, %s)' % (code, msg[0], msg[1])

  def openurl(self, url, params = {}):
    data = urllib.urlencode(params)
    try:
      return self.url_opener.open(url, data, timeout = 30)
    except urllib2.HTTPError, e:
      raise Exception('HTTP Error, Babelzilla server responded with ' + self.statusLine(e.code))
    except urllib2.URLError, e:
      raise Exception('Could not connect to Babelzilla server, reason: %s' % e.reason, start_response)

@url_handler('/babelzilla.php')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  try:
    connection = get_connection()
    languages = loadLanguageList(connection, get_config().get('abp', 'babelzilla_extension'))

    params = parse_qs(environ.get('QUERY_STRING', ''))
    langParam = params.get('language', [''])[0]
    if langParam:
      candidates = filter(lambda language: language['id'] == langParam or language['code'] == langParam, languages)
      if not candidates:
        raise Exception('Unknown language')

      language = candidates[0]
      data = downloadLanguage(connection, language, get_config().get('abp', 'babelzilla_extension'))
      checkResult = checkLanguage(language, data, get_config().get('abp', 'repository'))
      return showCheckResult(language, checkResult, start_response)
    else:
      return showLanguages(languages, start_response)
  except Exception, e:
    return showError(e, start_response)

@cached(3600)
def get_connection():
  return BabelzillaConnection(get_config().get('abp', 'babelzilla_user'),
                              get_config().get('abp', 'babelzilla_password'))

def loadLanguageList(connection, extensionID):
  try:
    response = connection.openurl('http://www.babelzilla.org/index2.php',
                                  {'option': 'com_wts', 'extension': extensionID, 'type': 'ajax', 'task': 'loadlist'})
  except Exception, e:
    raise Exception('Failed to load language list. %s' % str(e))

  languages = []
  for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', response.read().decode('utf-8'), re.S | re.I):
    cols = re.findall(r'<td\b[^>]*>(.*?)</td>', row)

    match = None
    if len(cols) >= 2:
      match = re.search(r'<a [^>]*href="[^">]*language=(\d+)[^">]*"[^>]*>([^<>&]+)', cols[1], re.I)
    if match:
      id, code = match.group(1), match.group(2)

      name = code
      m = re.search(r'<a\b[^>]*>([^<>&]+)', cols[0], re.I)
      if (m):
        name = m.group(1)

      status = 'unknown'
      if len(cols) >= 4:
        m = re.search(r'<b>(?:&nbsp;)*([^<>&]+)(?:&nbsp;)*</b>', cols[3], re.I)
      if m:
        status = m.group(1)
      languages.append({'id': id, 'code': code, 'name': name, 'status': status})
  return languages

def downloadLanguage(connection, language, extensionID):
  try:
    return connection.openurl('http://www.babelzilla.org/index2.php?' +
                              urllib.urlencode({'option': 'com_wts', 'Itemid': '88', 'type': 'localeskipped', 'extension': extensionID, 'language': language['id']}))
  except Exception, e:
    raise Exception('Failed to download locale. %s' % str(e))

def checkLanguage(language, data, repository):
  tempdir = tempfile.mkdtemp(prefix='adblockplus')
  try:
    subprocess.Popen(['hg', 'clone',  repository, tempdir], stdout=subprocess.PIPE).communicate()
    localeDir = os.path.join(tempdir, 'chrome', 'locale', language['code'])
    if not os.path.exists(localeDir):
      os.mkdir(localeDir)

    # Hack: have to use StringIO because current gzip implementation will seek on the stream
    archive = tarfile.open(fileobj=StringIO(data.read()), mode='r:gz')
    fileInfo = archive.next()
    while fileInfo:
      info = fileInfo
      fileInfo = archive.next()

      baseName = os.path.basename(info.name)
      if not info.isfile() or not baseName or baseName[0] == '.':
        continue
      file = open(os.path.join(localeDir, baseName), 'wb')
      file.writelines(archive.extractfile(info))
      file.close()
    archive.close()

    testScript = os.path.join(tempdir, 'test_locales.pl')
    os.chmod(testScript, 0755)
    popen = subprocess.Popen(['perl', testScript, language['code']], stdout=subprocess.PIPE)

    errors = []
    for line in popen.stdout:
      if not re.search(r"'abp:", line):
        continue
      line = line.decode('utf-8').strip()
      line = re.sub(r"^[\w\-]+: ", '', line)
      line = re.sub(r"'abp:global", "'global.properties", line)
      line = re.sub(r"'abp:meta", "'meta.properties", line)
      line = re.sub(r"'abp:(\w+)", r"'\1.dtd", line)
      line = re.sub(r"'(\w+\.(?:dtd|properties)):", r"'\1 -> ", line)

      critical = True
      if re.search('probably an untranslated string', line):
        critical = False

      errors.append({'text': line, 'critical': critical})

    popen.wait()
    if popen.returncode:
      raise Exception('Locale testing script exited with code %i' % popen.returncode)

    return errors
  finally:
    shutil.rmtree(tempdir)

def showLanguages(languages, start_response):
  template = get_template(get_config().get('abp', 'languagesTemplate'))

  start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
  return [template.render({'languages': languages}).encode('utf-8')]

def showCheckResult(language, errors, start_response):
  template = get_template(get_config().get('abp', 'languageCheckTemplate'))
  start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
  return [template.render({'errors': errors, 'language': language}).encode('utf-8')]

def showError(message, start_response):
  template = get_template(get_config().get('abp', 'errorTemplate'))
  start_response('400 Processing Error', [('Content-Type', 'text/html; charset=utf-8')])
  return [template.render({'message': message}).encode('utf-8')]
