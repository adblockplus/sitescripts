# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import hashlib
from sitescripts.utils import get_config, get_template, sendMail

def saveReport(reportData, file):
  template = get_template(get_config().get('reports', 'webTemplate'))
  template.stream(reportData).dump(file, encoding='utf-8')

def mailDigest(templateData):
  sendMail(get_config().get('reports', 'digestTemplate'), templateData)

def sendUpdateNotification(templateData):
  sendMail(get_config().get('reports', 'notificationTemplate'), templateData)

def calculateReportSecret(guid):
  hash = hashlib.md5()
  hash.update(get_config().get('reports', 'secret'))
  hash.update(guid)
  return hash.hexdigest()
