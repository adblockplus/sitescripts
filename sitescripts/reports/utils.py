# coding: utf-8

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
