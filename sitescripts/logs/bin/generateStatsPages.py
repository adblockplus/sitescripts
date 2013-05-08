# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2013 Eyeo GmbH
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

import os, re, time
from datetime import date, timedelta
from sitescripts.utils import get_config, setupStderr, get_template
from sitescripts.logs.countryCodes import countryCodes
from ConfigParser import SafeConfigParser

def getSubscriptionFiles(data, month):
  result = {}
  if data.has_section(month):
    for option in data.options(month):
      result[option[0:option.index(' ')]] = True
  return result

def generateMainPage(data, outputDir):
  def getDataInt(month, key):
    if data.has_option(month, key):
      return data.getint(month, key)
    else:
      return 0

  month = date.today().strftime('%Y%m')
  subscriptions = []
  for fileName in getSubscriptionFiles(data, month).iterkeys():
    subscriptions.append({
      'fileName': fileName,
      'url': 'subscription_%s_%s.html' % (re.sub(r'\W', '_', fileName), month),
      'hits': getDataInt(month, '%s hits' % fileName),
      'bandwidth': getDataInt(month, '%s bandwidth' % fileName)
    })
  subscriptions = sorted(subscriptions, key=lambda s: s['hits'], reverse=True)

  file = os.path.join(outputDir, 'index.html')
  template = get_template(get_config().get('subscriptionStats', 'mainPageTemplate'))
  template.stream({'now': time.time(), 'month': month, 'subscriptions': subscriptions}).dump(file)

def generateSubscriptionPages(data, outputDir):
  existingSubscriptions = {}
  template = get_template(get_config().get('subscriptionStats', 'subscriptionPageTemplate'))
  for month in data.sections():
    subscriptions = {}
    for option in data.options(month):
      spaceIndex = option.index(' ')
      if spaceIndex < 0:
        continue
      fileName, key = option[0:spaceIndex], option[spaceIndex+1:]
      existingSubscriptions[fileName] = True
      if not fileName in subscriptions:
        subscriptions[fileName] = {
          'now': time.time(),
          'month': month,
          'daysInMonth': (date(int(month[0:4]), int(month[4:]), 1) - timedelta(days=1)).day,
          'currentMonth': month == date.today().strftime('%Y%m'),
          'fileName': fileName,
          'overviewURL': 'overview_%s.html' % re.sub(r'\W', '_', fileName),
          'hits': 0,
          'bandwidth': 0,
          'day': {},
          'weekday': [{'id': i, 'hits': 0, 'bandwidth': 0, 'count': 0}for i in range(7)],
          'hour': {},
          'country': {},
          'app': {},
          'mirror': {},
        }
      if key == 'hits' or key == 'bandwidth':
        subscriptions[fileName][key] = data.getint(month, option)
      else:
        match = re.search(r'^(hits|bandwidth) (day|hour|country|app|mirror) (.*)$', key)
        if match:
          if not match.group(3) in subscriptions[fileName][match.group(2)]:
            subscriptions[fileName][match.group(2)][match.group(3)] = {
              'id': match.group(3),
              'hits': 0,
              'bandwidth': 0,
            }
            if match.group(2) == 'day':
              subscriptions[fileName][match.group(2)][match.group(3)]['weekday'] = date(int(month[0:4]), int(month[4:]), int(match.group(3))).weekday()
            if match.group(2) == 'country':
              if match.group(3) in countryCodes:
                subscriptions[fileName][match.group(2)][match.group(3)]['name'] = countryCodes[match.group(3)]
                subscriptions[fileName][match.group(2)][match.group(3)]['image'] = match.group(3)
              else:
                subscriptions[fileName][match.group(2)][match.group(3)]['name'] = 'Unknown'
                subscriptions[fileName][match.group(2)][match.group(3)]['image'] = 'ip'
          subscriptions[fileName][match.group(2)][match.group(3)][match.group(1)] = data.getint(month, option)

    for subscription in subscriptions.itervalues():
      for key in ('day', 'hour'):
        subscription[key] = sorted(subscription[key].itervalues(), key=lambda s: int(s['id']))
      for key in ('country', 'app', 'mirror'):
        subscription[key] = sorted(subscription[key].itervalues(), key=lambda s: s['hits'], reverse=True)
      for dayInfo in subscription['day']:
        weekdayInfo = subscription['weekday'][dayInfo['weekday']]
        weekdayInfo['hits'] = (weekdayInfo['hits'] * weekdayInfo['count'] + dayInfo['hits']) / (weekdayInfo['count'] + 1)
        weekdayInfo['bandwidth'] = (weekdayInfo['bandwidth'] * weekdayInfo['count'] + dayInfo['bandwidth']) / (weekdayInfo['count'] + 1)
        weekdayInfo['count'] += 1
      fileName = 'subscription_%s_%s.html' % (re.sub(r'\W', '_', subscription['fileName']), month)
      template.stream(subscription).dump(os.path.join(outputDir, fileName))
  return existingSubscriptions

def generateOverviewPage(data, outputDir, fileName):
  months = []
  for month in data.sections():
    if data.has_option(month, '%s hits' % fileName) and data.has_option(month, '%s bandwidth' % fileName):
      months.append({
        'id': month,
        'url': 'subscription_%s_%s.html' % (re.sub(r'\W', '_', fileName), month),
        'hits': data.getint(month, '%s hits' % fileName),
        'bandwidth': data.getint(month, '%s bandwidth' % fileName),
      })
  months = sorted(months, key=lambda m: m['id'])

  file = os.path.join(outputDir, 'overview_%s.html' % re.sub(r'\W', '_', fileName))
  template = get_template(get_config().get('subscriptionStats', 'subscriptionOverviewTemplate'))
  template.stream({'now': time.time(), 'fileName': fileName, 'month': months}).dump(file)

if __name__ == '__main__':
  setupStderr()

  data = SafeConfigParser()
  data.read(get_config().get('subscriptionStats', 'mainFile'))

  outputDir = get_config().get('subscriptionStats', 'outputDirectory')
  if not os.path.exists(outputDir):
    os.makedirs(outputDir)
  generateMainPage(data, outputDir)
  subscriptions = generateSubscriptionPages(data, outputDir)
  for fileName in subscriptions.iterkeys():
    generateOverviewPage(data, outputDir, fileName)
