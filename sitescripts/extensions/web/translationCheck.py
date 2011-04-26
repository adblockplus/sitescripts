# coding: utf-8

import urllib, urllib2, cookielib, re, string, tempfile, os, subprocess, tarfile, shutil, traceback
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
from sitescripts.utils import get_config, get_template, setupStderr, cached
from sitescripts.web import url_handler
from urlparse import parse_qs

@url_handler('/babelzilla.php')
def handleRequest(environ, start_response):
  setupStderr(environ['wsgi.errors'])

  try:
    params = parse_qs(environ.get('QUERY_STRING', ''))
    locale = params.get('language', [''])[0]
    if locale:
      if re.search(r'[^\w\-]', locale):
        raise Exception('Invalid locale name, use something like "pt-BR" or "fr"')

      data = downloadLanguage(locale, get_config().get('extensions', 'abp_babelzilla_extension'))
      checkResult = checkLanguage(locale, data, get_config().get('extensions', 'abp_repository'), get_config().get('extensions', 'buildRepository'))
      return showCheckResult(locale, checkResult, start_response)
    else:
      return showForm(start_response)
  except Exception, e:
    traceback.print_exc()
    return showError(e, start_response)

def downloadLanguage(locale, extensionID):
  try:
    url = 'http://www.babelzilla.org/wts/download/locale/%s/skipped/%s' % (locale, extensionID)
    return urllib2.urlopen(url, timeout=30)
  except Exception, e:
    raise Exception('Failed to download locale. %s' % str(e))

def checkLanguage(locale, data, repository, buildRepository):
  tempdir = tempfile.mkdtemp(prefix='adblockplus')
  try:
    command = ['hg', 'archive',  '-q', '-R', repository, '-r', 'default', tempdir]
    subprocess.Popen(command, stdout=subprocess.PIPE).communicate()
    try:
      command = ['hg', 'archive', '-q', '-R', buildRepository, '-r', 'default', os.path.join(tempdir, 'buildtools')]
      subprocess.Popen(command).communicate()
    except:
      pass
    localeDir = os.path.join(tempdir, 'chrome', 'locale', locale)
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
    popen = subprocess.Popen(['perl', testScript, locale], stdout=subprocess.PIPE)

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

def showForm(start_response):
  template = get_template(get_config().get('extensions', 'languageFormTemplate'))

  start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
  return [template.render().encode('utf-8')]

def showCheckResult(locale, errors, start_response):
  template = get_template(get_config().get('extensions', 'languageCheckTemplate'))
  start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
  return [template.render({'errors': errors, 'locale': locale}).encode('utf-8')]

def showError(message, start_response):
  template = get_template(get_config().get('extensions', 'errorTemplate'))
  start_response('400 Processing Error', [('Content-Type', 'text/html; charset=utf-8')])
  return [template.render({'message': message}).encode('utf-8')]
