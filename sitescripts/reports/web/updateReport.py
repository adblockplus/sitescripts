# coding: utf-8

import re, os, sys, marshal, random
from urlparse import parse_qsl
from sitescripts.utils import get_config, get_template
from sitescripts.reports.utils import calculateReportSecret, saveReport, sendUpdateNotification

def handleReportUpdateRequest(environ, start_response):
  if environ['REQUEST_METHOD'].upper() != 'POST' or not environ.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded'):
    return showError('Unsupported request method', start_response)

  try:
    request_body_length = int(environ['CONTENT_LENGTH'])
  except:
    return showError('Invalid or missing Content-Length header', start_response)

  request_body = environ['wsgi.input'].read(request_body_length)
  params = {}
  for key, value in parse_qsl(request_body):
    params[key] = value.decode('utf-8')

  guid = params.get('guid', '').lower()
  if not re.match(r'^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$', guid):
    return showError('Invalid or missing report GUID', start_response)

  path = os.path.join(get_config().get('reports', 'dataPath'), guid[0], guid[1], guid[2], guid[3], guid + '.dump')
  if not os.path.exists(path):
    return showError('Report does not exists', start_response)

  secret = calculateReportSecret(guid)
  if params.get('secret', '') != secret:
    return showError('Wrong secret value', start_response)

  handle = open(path, 'rb')
  reportData = marshal.load(handle)
  handle.close()

  reportData['status'] = params.get('status', '')
  if len(reportData['status']) > 1024:
    reportData['status'] = reportData['status'][:1024]

  handle = open(path, 'wb')
  marshal.dump(reportData, handle)
  handle.close()

  saveReport(reportData, re.sub(r'\.dump', '.html', path))

  if params.get('notify', '') and 'email' in reportData:
    email = reportData['email']
    email = re.sub(r' at ', r'@', email)
    email = re.sub(r' dot ', r'.', email)
    if re.match(r'^[\w.%+-]+@[\w.%+-]+(\.[\w.%+-]+)+', email):
      sendUpdateNotification({
        'email': email,
        'url': get_config().get('reports', 'urlRoot') + guid,
        'status': reportData['status'],
      })

  newURL = get_config().get('reports', 'urlRoot') + guid
  newURL += '?updated=' + str(int(random.uniform(0, 10000)))
  newURL += '#secret=' + secret
  start_response('302 Found', [('Location', newURL.encode('utf-8'))])
  return []

def showError(message, start_response):
  template = get_template(get_config().get('reports', 'errorTemplate'))
  start_response('400 Processing Error', [('Content-Type', 'application/xhtml+xml; charset=utf-8')])
  return [template.render({'message': message}).encode('utf-8')]
