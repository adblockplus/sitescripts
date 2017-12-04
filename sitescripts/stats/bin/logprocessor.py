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

import argparse
import codecs
from collections import OrderedDict
from datetime import datetime, timedelta
import errno
import functools
import gzip
import json
import math
import multiprocessing
import numbers
import os
import re
import pygeoip
import socket
import subprocess
import sys
import traceback
import urllib
import urlparse

import sitescripts.stats.common as common
from sitescripts.utils import get_config, setupStderr

log_regexp = None
KNOWN_APPS = {
    '{55aba3ac-94d3-41a8-9e25-5c21fe874539}': 'adblockbrowser',
    '{a79fe89b-6662-4ff4-8e88-09950ad4dfde}': 'conkeror',
    'dlm@emusic.com': 'emusic',
    '{a23983c0-fd0e-11dc-95ff-0800200c9a66}': 'fennec',
    '{aa3c5121-dab2-40e2-81ca-7ea25febc110}': 'fennec2',
    '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}': 'firefox',
    '{aa5ca914-c309-495d-91cf-3141bbb04115}': 'midbrowser',
    'prism@developer.mozilla.org': 'prism',
    '{92650c4d-4b8e-4d2a-b7eb-24ecf4f6b63a}': 'seamonkey',
    'songbird@songbirdnest.com': 'songbird',
    '{3550f703-e582-4d05-9a08-453d09bdfdc6}': 'thunderbird',
    'toolkit@mozilla.org': 'toolkit',
}


class StatsFile:
    def __init__(self, path):
        self._inner_file = None
        self._processes = []

        parseresult = urlparse.urlparse(path)
        if parseresult.scheme == 'ssh' and parseresult.username and parseresult.hostname and parseresult.path:
            command = [
                'ssh', '-q', '-o', 'NumberOfPasswordPrompts 0', '-T', '-k',
                '-l', parseresult.username,
                parseresult.hostname,
                parseresult.path.lstrip('/')
            ]
            if parseresult.port:
                command[1:1] = ['-P', str(parseresult.port)]
            ssh_process = subprocess.Popen(command, stdout=subprocess.PIPE)
            self._processes.append(ssh_process)
            self._file = ssh_process.stdout
        elif parseresult.scheme in ('http', 'https'):
            self._file = urllib.urlopen(path)
        elif os.path.exists(path):
            self._file = open(path, 'rb')
        else:
            raise IOError("Path '%s' not recognized" % path)

        if path.endswith('.gz'):
            # Built-in gzip module doesn't support streaming (fixed in Python 3.2)
            gzip_process = subprocess.Popen(['gzip', '-cd'], stdin=self._file, stdout=subprocess.PIPE)
            self._processes.append(gzip_process)
            self._file, self._inner_file = gzip_process.stdout, self._file

    def __getattr__(self, name):
        return getattr(self._file, name)

    def close(self):
        self._file.close()
        if self._inner_file:
            self._inner_file.close()
        for process in self._processes:
            process.wait()


def get_stats_files():
    config = get_config()

    prefix = 'mirror_'
    options = filter(lambda o: o.startswith(prefix), config.options('stats'))
    for option in options:
        if config.has_option('stats', option):
            value = config.get('stats', option)
            if ' ' in value:
                yield [option[len(prefix):]] + value.split(None, 1)
            else:
                print >>sys.stderr, "Option '%s' has invalid value: '%s'" % (option, value)
        else:
            print >>sys.stderr, "Option '%s' not found in the configuration" % option


def cache_lru(func):
    """
      Decorator that memoizes the return values of a single-parameter function in
      case it is called again with the same parameter. The 1024 most recent
      results are saved.
    """

    results = OrderedDict()
    results.entries_left = 1024

    def wrapped(arg):
        if arg in results:
            result = results[arg]
            del results[arg]
        else:
            if results.entries_left > 0:
                results.entries_left -= 1
            else:
                results.popitem(last=False)
            try:
                result = func(arg)
            except:
                results.entries_left += 1
                raise
        results[arg] = result
        return result
    return wrapped


def cache_last(func):
    """
      Decorator that memoizes the last return value of a function in case it is
      called again with the same parameters.
    """
    result = {'args': None, 'result': None}

    def wrapped(*args):
        if args != result['args']:
            result['result'] = func(*args)
            result['args'] = args
        return result['result']
    return wrapped


@cache_lru
def parse_ua(ua):
    # Opera might disguise itself as other browser so it needs to go first
    match = re.search(r'\bOpera/([\d\.]+)', ua)
    if match:
        # Opera 10+ declares itself as Opera 9.80 but adds Version/1x.x to the UA
        match2 = re.search(r'\bVersion/([\d\.]+)', ua)
        if match2:
            return 'Opera', match2.group(1)
        else:
            return 'Opera', match.group(1)

    # Opera 15+ has the same UA as Chrome but adds OPR/1x.x to it
    match = re.search(r'\bOPR/(\d+\.\d+)', ua)
    if match:
        return 'Opera', match.group(1)

    # Have to check for these before Firefox, they will usually have a Firefox identifier as well
    match = re.search(r'\b(Fennec|Thunderbird|SeaMonkey|Songbird|K-Meleon|Prism)/(\d+\.\d+)', ua)
    if match:
        if match.group(1) == 'Fennec':
            return 'Firefox Mobile', match.group(2)
        else:
            return match.group(1), match.group(2)

    match = re.search(r'\bFirefox/(\d+\.\d+)', ua)
    if match:
        if re.search(r'\bMobile;', ua):
            return 'Firefox Mobile', match.group(1)
        elif re.search(r'\bTablet;', ua):
            return 'Firefox Tablet', match.group(1)
        else:
            return 'Firefox', match.group(1)

    match = re.search(r'\brv:(\d+)\.(\d+)(?:\.(\d+))?', ua)
    if match and re.search(r'\bGecko/', ua):
        if match.group(3) and int(match.group(1)) < 2:
            return 'Gecko', '%s.%s.%s' % (match.group(1), match.group(2), match.group(3))
        else:
            return 'Gecko', '%s.%s' % (match.group(1), match.group(2))

    match = re.search(r'\bCoolNovo/(\d+\.\d+\.\d+)', ua)
    if match:
        return 'CoolNovo', match.group(1)

    match = re.search(r'\bEdge/(\d+)\.\d+', ua)
    if match:
        return 'Edge', match.group(1)

    match = re.search(r'\bChrome/(\d+\.\d+)', ua)
    if match:
        return 'Chrome', match.group(1)

    match = re.search(r'\bVersion/(\d+\.\d+)', ua)
    if match and re.search(r'\bMobile Safari/', ua):
        return 'Mobile Safari', match.group(1)
    if match and re.search(r'\bSafari/', ua):
        return 'Safari', match.group(1)

    if re.search(r'\bAppleWebKit/', ua):
        return 'WebKit', ''

    match = re.search(r'\bMSIE (\d+\.\d+)', ua)
    if match:
        return 'MSIE', match.group(1)

    match = re.search(r'\bTrident/(\d+\.\d+)', ua)
    if match:
        match2 = re.search(r'\brv:(\d+\.\d+)', ua)
        if match2:
            return 'MSIE', match2.group(1)
        else:
            return 'Trident', match.group(1)

    match = re.search(r'\bAndroidDownloadManager(?:/(\d+\.\d+))?', ua)
    if match:
        return 'Android', match.group(1) or ''

    match = re.search(r'\bDalvik/.*\bAndroid (\d+\.\d+)', ua)
    if match:
        return 'Android', match.group(1)

    # ABP/Android downloads use that user agent
    if ua.startswith('Apache-HttpClient/UNAVAILABLE'):
        return 'Android', ''

    # ABP/IE downloads use that user agent
    if ua == 'Adblock Plus':
        return 'ABP', ''

    return 'Other', ''


def process_ip(ip, geo, geov6):
    match = re.search(r'^::ffff:(\d+\.\d+\.\d+\.\d+)$', ip)
    if match:
        ip = match.group(1)

    try:
        if ':' in ip:
            country = geov6.country_code_by_addr(ip)
        else:
            country = geo.country_code_by_addr(ip)
    except:
        traceback.print_exc()
        country = ''

    if country in (None, '', '--'):
        country = 'unknown'
    country = country.lower()

    return ip, country


@cache_last
def parse_time(timestr, tz_hours, tz_minutes):
    result = datetime.strptime(timestr, '%d/%b/%Y:%H:%M:%S')
    result -= timedelta(hours=tz_hours, minutes=math.copysign(tz_minutes, tz_hours))
    return result, result.strftime('%Y%m'), result.day, result.weekday(), result.hour


@cache_lru
def parse_path(path):
    urlparts = urlparse.urlparse(path)
    try:
        path = urllib.unquote(urlparts.path).decode('utf-8')
    except:
        path = urlparts.path
    return path[1:], urlparts.query


@cache_lru
def parse_query(query):
    return urlparse.parse_qs(query)


@cache_lru
def parse_lastversion(last_version):
    if '-' in last_version:
        last_version = last_version.split('-', 1)[0]
    return datetime.strptime(last_version, '%Y%m%d%H%M')


@cache_lru
def get_week(date):
    return date.isocalendar()[0:2]


def parse_downloader_query(info):
    params = parse_query(info['query'])
    for param in ('addonName', 'addonVersion', 'application', 'applicationVersion', 'platform', 'platformVersion'):
        info[param] = params.get(param, ['unknown'])[0]

    # Only leave the major and minor release number for application and platform
    info['applicationVersion'] = re.sub(r'^(\d+\.\d+).*', r'\1', info['applicationVersion'])
    info['platformVersion'] = re.sub(r'^(\d+\.\d+).*', r'\1', info['platformVersion'])

    # Chrome Adblock sends an X-Client-ID header insteads of URL parameters
    match = re.match(r'^adblock/([\d\.]+)$', info['clientid'], re.I) if info['clientid'] else None
    if match:
        info['addonName'] = 'chromeadblock'
        info['addonVersion'] = match.group(1)

    last_version = params.get('lastVersion', ['unknown'])[0]
    if info['file'] == 'notification.json' and last_version == '0' and (
        (info['addonName'] == 'adblockplus' and info['addonVersion'] == '2.3.1') or
        (info['addonName'] in ('adblockpluschrome', 'adblockplusopera') and info['addonVersion'] == '1.5.2')
    ):
        # Broken notification version number in these releases, treat like unknown
        last_version = 'unknown'

    if last_version == 'unknown':
        info['downloadInterval'] = 'unknown'
        info['previousDownload'] = 'unknown'
    elif last_version == '0':
        info['downloadInterval'] = 'unknown'
        info['previousDownload'] = 'unknown'
        info['firstDownload'] = True
    else:
        try:
            last_update = parse_lastversion(last_version)
            diff = info['time'] - last_update
            if diff.days >= 365:
                info['downloadInterval'] = '%i year(s)' % (diff.days / 365)
            elif diff.days >= 30:
                info['downloadInterval'] = '%i month(s)' % (diff.days / 30)
            elif diff.days >= 1:
                info['downloadInterval'] = '%i day(s)' % diff.days
            else:
                info['downloadInterval'] = '%i hour(s)' % (diff.seconds / 3600)

            if info['addonName'].startswith('adblockplus'):
                diffdays = (info['time'].date() - last_update.date()).days
                if diffdays == 0:
                    info['previousDownload'] = 'same day'
                elif diffdays < 30:
                    info['previousDownload'] = '%i day(s)' % diffdays
                elif diffdays < 365:
                    info['previousDownload'] = '%i month(s)' % (diffdays / 30)
                else:
                    info['previousDownload'] = '%i year(s)' % (diffdays / 365)
            else:
                info['previousDownload'] = 'unknown'

            if last_update.year != info['time'].year or last_update.month != info['time'].month:
                info['firstInMonth'] = info['firstInDay'] = True
            elif last_update.day != info['time'].day:
                info['firstInDay'] = True

            if get_week(last_update) != get_week(info['time']):
                info['firstInWeek'] = True
        except ValueError:
            info['downloadInterval'] = 'unknown'
            info['previousDownload'] = 'unknown'
            pass


def parse_addon_name(file):
    if '/' in file:
        return file.split('/')[-2]
    else:
        return None


def parse_gecko_query(query):
    params = urlparse.parse_qs(query)

    version = params.get('version', ['unknown'])[0]

    appID = params.get('appID', ['unknown'])[0]

    application = KNOWN_APPS.get(appID, 'unknown')
    applicationVersion = params.get('appVersion', ['unknown'])[0]

    # Only leave the major and minor release number for application
    applicationVersion = re.sub(r'^(\d+\.\d+).*', r'\1', applicationVersion)

    return version, application, applicationVersion


def parse_chrome_query(query):
    params = urlparse.parse_qs(query)

    if params.get('prod', ['unknown'])[0] in ('chromecrx', 'chromiumcrx'):
        application = 'chrome'
    else:
        application = 'unknown'
    applicationVersion = params.get('prodversion', ['unknown'])[0]

    params2 = urlparse.parse_qs(params.get('x', [''])[0])
    version = params2.get('v', ['unknown'])[0]

    # Only leave the major and minor release number for application
    applicationVersion = re.sub(r'^(\d+\.\d+).*', r'\1', applicationVersion)

    return version, application, applicationVersion


def parse_update_flag(query):
    return 'update' if query == 'update' else 'install'


def parse_record(line, ignored, geo, geov6):
    global log_regexp
    if log_regexp == None:
        log_regexp = re.compile(r'(\S+) \S+ \S+ \[([^]\s]+) ([+\-]\d\d)(\d\d)\] "GET ([^"\s]+) [^"]+" (\d+) (\d+) "([^"]*)" "([^"]*)"(?: "[^"]*" \S+ "[^"]*" "[^"]*" "([^"]*)")?')

    match = re.search(log_regexp, line)
    if not match:
        return None

    status = int(match.group(6))
    if status not in (200, 301, 302):
        return None

    info = {
        'status': status,
        'size': int(match.group(7)),
    }

    info['ip'], info['country'] = process_ip(match.group(1), geo, geov6)
    info['time'], info['month'], info['day'], info['weekday'], info['hour'] = parse_time(match.group(2), int(match.group(3)), int(match.group(4)))
    info['file'], info['query'] = parse_path(match.group(5))
    info['referrer'] = match.group(8)
    info['ua'], info['uaversion'] = parse_ua(match.group(9))
    info['fullua'] = '%s %s' % (info['ua'], info['uaversion'])
    info['clientid'] = match.group(10)

    # Additional metadata depends on file type
    filename = os.path.basename(info['file'])
    ext = os.path.splitext(filename)[1]
    if ext == '.txt' or filename == 'update.json' or filename == 'notification.json':
        # Subscription downloads, libadblockplus update checks and notification
        # checks are performed by the downloader
        parse_downloader_query(info)
    elif ext == '.tpl':
        # MSIE TPL download, no additional data here
        pass
    elif ext in ('.xpi', '.crx', '.apk', '.msi', '.exe', '.safariextz'):
        # Package download, might be an update
        info['installType'] = parse_update_flag(info['query'])
    elif filename == 'update.rdf':
        # Gecko update check or a legacy Android update check. The latter doesn't
        # have usable data anyway so trying the Chrome route won't do any harm.
        info['addonName'] = parse_addon_name(info['file'])
        info['addonVersion'], info['application'], info['applicationVersion'] = parse_gecko_query(info['query'])
    elif filename == 'updates.xml':
        # Chrome update check
        info['addonName'] = parse_addon_name(info['file'])
        info['addonVersion'], info['application'], info['applicationVersion'] = parse_chrome_query(info['query'])
    elif filename == 'updates.plist':
        # Safari update check, no additional data
        pass
    else:
        ignored.add(info['file'])
        return None

    if 'addonName' in info:
        info['fullAddon'] = '%s %s' % (info['addonName'], info['addonVersion'])
    if 'application' in info:
        info['fullApplication'] = '%s %s' % (info['application'], info['applicationVersion'])
    if 'platform' in info:
        info['fullPlatform'] = '%s %s' % (info['platform'], info['platformVersion'])
    return info


def add_record(info, section, ignore_fields=()):
    section['hits'] = section.get('hits', 0) + 1
    section['bandwidth'] = section.get('bandwidth', 0) + info['size']

    if len(ignore_fields) < 2:
        for field in map(lambda f: f['name'], common.fields):
            if field in ignore_fields or field not in info:
                continue

            value = info[field]
            if field not in section:
                section[field] = {}
            if value not in section[field]:
                section[field][value] = {}

            add_record(info, section[field][value], ignore_fields + (field,))


def parse_fileobj(mirror_name, fileobj, geo, geov6, ignored):
    data = {}
    for line in fileobj:
        info = parse_record(line, ignored, geo, geov6)
        if info == None:
            continue

        info['mirror'] = mirror_name
        if info['month'] not in data:
            data[info['month']] = {}
        section = data[info['month']]

        if info['file'] not in section:
            section[info['file']] = {}
        section = section[info['file']]

        add_record(info, section)
    return data


def merge_objects(object1, object2, factor=1):
    for key, value in object2.iteritems():
        try:
            key = unicode(key)
        except UnicodeDecodeError:
            key = unicode(key, encoding='latin-1')
        if isinstance(value, numbers.Number):
            object1[key] = object1.get(key, 0) + factor * value
        else:
            merge_objects(object1.setdefault(key, {}), value, factor)


def save_stats(server_type, data, factor=1):
    base_dir = os.path.join(get_config().get('stats', 'dataDirectory'), common.filename_encode(server_type))
    for month, month_data in data.iteritems():
        for name, file_data in month_data.iteritems():
            path = os.path.join(base_dir, common.filename_encode(month), common.filename_encode(name + '.json'))
            if os.path.exists(path):
                with codecs.open(path, 'rb', encoding='utf-8') as fileobj:
                    existing = json.load(fileobj)
            else:
                existing = {}

            merge_objects(existing, file_data, factor)

            dir = os.path.dirname(path)
            try:
                os.makedirs(dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            with codecs.open(path, 'wb', encoding='utf-8') as fileobj:
                json.dump(existing, fileobj, indent=2, sort_keys=True)


def parse_source(factor, lock, (mirror_name, server_type, log_file)):
    try:
        geo = pygeoip.GeoIP(get_config().get('stats', 'geoip_db'), pygeoip.MEMORY_CACHE)
        geov6 = pygeoip.GeoIP(get_config().get('stats', 'geoipv6_db'), pygeoip.MEMORY_CACHE)

        ignored = set()
        fileobj = StatsFile(log_file)
        try:
            data = parse_fileobj(mirror_name, fileobj, geo, geov6, ignored)
        finally:
            fileobj.close()

        lock.acquire()
        try:
            save_stats(server_type, data, factor)
        finally:
            lock.release()
        return log_file, ignored
    except:
        print >>sys.stderr, "Unable to process log file '%s'" % log_file
        traceback.print_exc()
        return None, None


def parse_sources(sources, factor=1, verbose=False):
    pool = multiprocessing.Pool()
    lock = multiprocessing.Manager().Lock()
    callback = functools.partial(parse_source, factor, lock)
    try:
        for log_file, ignored in pool.imap_unordered(callback, sources, chunksize=1):
            if verbose and ignored:
                print 'Ignored files for %s' % log_file
                print '============================================================'
                print '\n'.join(sorted(ignored))
    finally:
        pool.close()


if __name__ == '__main__':
    setupStderr()

    parser = argparse.ArgumentParser(description='Processes log files and merges them into the stats database')
    parser.add_argument('--verbose', dest='verbose', action='store_const', const=True, default=False, help='Verbose mode, ignored requests will be listed')
    parser.add_argument('--revert', dest='factor', action='store_const', const=-1, default=1, help='Remove log data from the database')
    parser.add_argument('mirror_name', nargs='?', help='Name of the mirror server that the file belongs to')
    parser.add_argument('server_type', nargs='?', help='Server type like download, update or subscription')
    parser.add_argument('log_file', nargs='?', help='Log file path, can be a local file path, http:// or ssh:// URL')
    args = parser.parse_args()

    if args.mirror_name and args.server_type and args.log_file:
        sources = [(args.mirror_name, args.server_type, args.log_file)]
    else:
        sources = get_stats_files()
    parse_sources(sources, args.factor, args.verbose)
