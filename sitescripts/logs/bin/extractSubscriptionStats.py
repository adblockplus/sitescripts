# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import sys, re, math, GeoIP
from sitescripts.utils import get_config, setupStderr
from datetime import datetime, timedelta
from ConfigParser import SafeConfigParser, NoOptionError

def parseUA(ua):
  # Opera might disguise itself as other browser so it needs to go first
  match = re.search(r'\bOpera/([\d\.]+)', ua)
  if match:
    return 'Opera %s' % match.group(1)

  for appName in ('Fennec', 'Thunderbird', 'SeaMonkey', 'Songbird', 'K-Meleon', 'Prism', 'Firefox'):
    match = re.search(r'\b%s/(\d+\.\d+)' % appName, ua)
    if match:
      return '%s %s' % (appName, match.group(1))

  match = re.search(r'\brv:(\d+)\.(\d+)(?:\.(\d+))?', ua)
  if match and re.search(r'\bGecko/', ua):
    if match.group(3) and int(match.group(1)) < 2:
      return 'Gecko %s.%s.%s' % (match.group(1), match.group(2), match.group(3))
    else:
      return 'Gecko %s.%s' % (match.group(1), match.group(2))

  match = re.search(r'\bChrome/(\d+\.\d+)', ua)
  if match:
    return 'Chrome %s' % match.group(1)

  match = re.search(r'\bVersion/(\d+\.\d+)', ua)
  if match and re.search(r'\Safari/', ua):
    return 'Safari %s' % match.group(1)

  if re.search(r'\bAppleWebKit/', ua):
    return 'WebKit'

  match = re.search(r'\bMSIE (\d+\.\d+)', ua)
  if match:
    return 'MSIE %s' % match.group(1)

  return 'Other'

def parseStdIn(geo):
  if get_config().has_option('logs', 'subscriptionsSubdir'):
    subdir = get_config().get('logs', 'subscriptionsSubdir')
    subdir = re.sub(r'^/+', '', subdir)
    subdir = re.sub(r'/+$', '', subdir)
    subdir = re.sub(r'(?=\W)', r'\\', subdir)
    subdir = subdir + '/'
  else:
    subdir = ''
  regexp = re.compile(r'(\S+) \S+ \S+ \[([^]\s]+) ([+\-]\d\d)(\d\d)\] "GET (?:\w+://[^/]+)?/%s([\w\-\+\.]+\.(?:txt|tpl)) [^"]+" (\d+) (\d+) "[^"]*" "([^"]*)"' % subdir)

  data = {}
  for line in sys.stdin:
    match = re.search(regexp, line)
    if not match:
      continue

    ip, time, tzHours, tzMinutes = match.group(1), match.group(2), int(match.group(3)), int(match.group(4))
    file, status, size, ua = match.group(5), int(match.group(6)), int(match.group(7)), match.group(8)
    if status != 200 and status != 302 and status != 304:
      continue
    if file.startswith('robots.'):
      continue

    time = datetime.strptime(time, '%d/%b/%Y:%H:%M:%S')
    time -= timedelta(hours = tzHours, minutes = math.copysign(tzMinutes, tzHours))

    match = re.search(r'^::ffff:(\d+\.\d+\.\d+\.\d+)$', ip)
    if match:
      ip = match.group(1)
    country = geo.country_code_by_addr(ip)
    if country == '' or country == '--':
      country = 'unknown'

    ua = parseUA(ua)

    section = time.strftime('%Y%m')
    if not section in data:
      data[section] = {}

    def addResultInt(key, value):
      if key in data[section]:
        data[section][key] += value
      else:
        data[section][key] = value

    addResultInt('%s hits' % file, 1)
    addResultInt('%s bandwidth' % file, size)
    addResultInt('%s hits day %i' % (file, time.day), 1)
    addResultInt('%s bandwidth day %i' % (file, time.day), size)
    addResultInt('%s hits hour %i' % (file, time.hour), 1)
    addResultInt('%s bandwidth hour %i' % (file, time.hour), size)
    addResultInt('%s hits country %s' % (file, country), 1)
    addResultInt('%s bandwidth country %s' % (file, country), size)
    addResultInt('%s hits app %s' % (file, ua), 1)
    addResultInt('%s bandwidth app %s' % (file, ua), size)

  result = SafeConfigParser()
  for section in data.iterkeys():
    result.add_section(section)
    for key, value in data[section].iteritems():
      result.set(section, key, str(value))
  return result

if __name__ == '__main__':
  setupStderr()

  geo = GeoIP.open(get_config().get('logs', 'geoip_db'), GeoIP.GEOIP_MEMORY_CACHE)
  result = parseStdIn(geo)

  file = open(get_config().get('subscriptionStats', 'tempFile'), 'wb')
  result.write(file)
