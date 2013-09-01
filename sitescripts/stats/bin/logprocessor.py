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

import os, sys, codecs, re, math, urllib, urlparse, socket, json
import pygeoip
from collections import OrderedDict
import sitescripts.stats.common as common
from sitescripts.utils import get_config, setupStderr
from datetime import datetime, timedelta

log_regexp = None
mirror_name = None
gecko_apps = None

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
      result = func(arg)
    results[arg] = result
    return result
  return wrapped


def cache_last(func):
  """
    Decorator that memoizes the last return value of a function in case it is
    called again with the same parameters.
  """
  result = {"args": None, "result": None}

  def wrapped(*args):
    if args != result["args"]:
      result["result"] = func(*args)
      result["args"] = args
    return result["result"]
  return wrapped


@cache_lru
def parse_ua(ua):
  # Opera might disguise itself as other browser so it needs to go first
  match = re.search(r"\bOpera/([\d\.]+)", ua)
  if match:
    # Opera 10+ declares itself as Opera 9.80 but adds Version/1x.x to the UA
    match2 = re.search(r"\bVersion/([\d\.]+)", ua)
    if match2:
      return "Opera", match2.group(1)
    else:
      return "Opera", match.group(1)

  # Opera 15+ has the same UA as Chrome but adds OPR/1x.x to it
  match = re.search(r"\bOPR/(\d+\.\d+)", ua)
  if match:
    return "Opera", match.group(1)

  # Have to check for these before Firefox, they will usually have a Firefox identifier as well
  match = re.search(r"\b(Fennec|Thunderbird|SeaMonkey|Songbird|K-Meleon|Prism)/(\d+\.\d+)", ua)
  if match:
    if match.group(1) == "Fennec":
      return "Firefox Mobile", match.group(2)
    else:
      return match.group(1), match.group(2)

  match = re.search(r"\bFirefox/(\d+\.\d+)", ua)
  if match:
    if re.search(r"\bMobile;", ua):
      return "Firefox Mobile", match.group(1)
    else:
      return "Firefox", match.group(1)

  match = re.search(r"\brv:(\d+)\.(\d+)(?:\.(\d+))?", ua)
  if match and re.search(r"\bGecko/", ua):
    if match.group(3) and int(match.group(1)) < 2:
      return "Gecko", "%s.%s.%s" % (match.group(1), match.group(2), match.group(3))
    else:
      return "Gecko", "%s.%s" % (match.group(1), match.group(2))

  match = re.search(r"\bCoolNovo/(\d+\.\d+\.\d+)", ua)
  if match:
    return "CoolNovo", match.group(1)

  match = re.search(r"\bChrome/(\d+\.\d+)", ua)
  if match:
    return "Chrome", match.group(1)

  match = re.search(r"\bVersion/(\d+\.\d+)", ua)
  if match and re.search(r"\bMobile Safari/", ua):
    return "Mobile Safari", match.group(1)
  if match and re.search(r"\bSafari/", ua):
    return "Safari", match.group(1)

  if re.search(r"\bAppleWebKit/", ua):
    return "WebKit", ""

  match = re.search(r"\bMSIE (\d+\.\d+)", ua)
  if match:
    return "MSIE", match.group(1)

  match = re.search(r"\bTrident/(\d+\.\d+)", ua)
  if match:
    return "Trident", match.group(1)

  match = re.search(r"\bAndroidDownloadManager(?:/(\d+\.\d+))?", ua)
  if match:
    return "Android", match.group(1) or ""

  match = re.search(r"\bDalvik/.*\bAndroid (\d+\.\d+)", ua)
  if match:
    return "Android", match.group(1)

  # ABP/Android downloads use that user agent
  if ua.startswith("Apache-HttpClient/UNAVAILABLE"):
    return "Android", ""

  # ABP/IE downloads use that user agent
  if ua == "Adblock Plus":
    return "ABP", ""

  return "Other", ""

def process_ip(ip, geo, geov6):
  match = re.search(r"^::ffff:(\d+\.\d+\.\d+\.\d+)$", ip)
  if match:
    ip = match.group(1)

  if ":" in ip:
    country = geov6.country_code_by_addr(ip)
  else:
    country = geo.country_code_by_addr(ip)
  if country in (None, "", "--"):
    country = "unknown"
  country = country.lower()

  return ip, country

@cache_last
def parse_time(timestr, tz_hours, tz_minutes):
  result = datetime.strptime(timestr, "%d/%b/%Y:%H:%M:%S")
  result -= timedelta(hours = tz_hours, minutes = math.copysign(tz_minutes, tz_hours))
  return result, result.strftime("%Y%m"), result.day, result.weekday(), result.hour

@cache_lru
def parse_path(path):
  urlparts = urlparse.urlparse(path)
  try:
    path = urllib.unquote(urlparts.path).decode("utf-8")
  except:
    path = urlparts.path
  return path[1:], urlparts.query

@cache_lru
def parse_query(query):
  return urlparse.parse_qs(query)

@cache_lru
def parse_lastversion(last_version):
  return datetime.strptime(last_version, "%Y%m%d%H%M")

@cache_lru
def get_week(date):
  return date.isocalendar()[0:2]

def parse_downloader_query(info):
  params = parse_query(info["query"])
  for param in ("addonName", "addonVersion", "application", "applicationVersion", "platform", "platformVersion"):
    info[param] = params.get(param, ["unknown"])[0]

  # Only leave the major and minor release number for application and platform
  info["applicationVersion"] = re.sub(r"^(\d+\.\d+).*", r"\1", info["applicationVersion"])
  info["platformVersion"] = re.sub(r"^(\d+\.\d+).*", r"\1", info["platformVersion"])

  # Chrome Adblock sends an X-Client-ID header insteads of URL parameters
  match = re.match(r"^adblock/([\d\.]+)$", info["clientid"], re.I) if info["clientid"] else None
  if match:
    info["addonName"] = "chromeadblock"
    info["addonVersion"] = match.group(1)

  last_version = params.get("lastVersion", ["unknown"])[0]
  if info["file"] == "notification.json" and last_version == "0" and (
      (info["addonName"] == "adblockplus" and info["addonVersion"] == "2.3.1") or
      (info["addonName"] in ("adblockpluschrome", "adblockplusopera") and info["addonVersion"] == "1.5.2")
    ):
    # Broken notification version number in these releases, treat like unknown
    last_version = "unknown"

  if last_version == "unknown":
    info["downloadInterval"] = "unknown"
  elif last_version == "0":
    info["downloadInterval"] = "unknown"
    info["firstDownload"] = True
  else:
    try:
      last_update = parse_lastversion(last_version)
      diff = info["time"] - last_update
      if diff.days >= 365:
        info["downloadInterval"] = "%i year(s)" % (diff.days / 365)
      elif diff.days >= 30:
        info["downloadInterval"] = "%i month(s)" % (diff.days / 30)
      elif diff.days >= 1:
        info["downloadInterval"] = "%i day(s)" % diff.days
      else:
        info["downloadInterval"] = "%i hour(s)" % (diff.seconds / 3600)

      if last_update.year != info["time"].year or last_update.month != info["time"].month:
        info["firstInMonth"] = info["firstInDay"] = True
      elif last_update.day != info["time"].day:
        info["firstInDay"] = True

      if get_week(last_update) != get_week(info["time"]):
        info["firstInWeek"] = True
    except ValueError:
      info["downloadInterval"] = "unknown"
      pass

def parse_addon_name(file):
  if "/" in file:
    return file.split("/")[-2]
  else:
    return None

def parse_gecko_query(query):
  params = urlparse.parse_qs(query)

  version = params.get("version", ["unknown"])[0]

  global gecko_apps
  if gecko_apps == None:
    from buildtools.packagerGecko import KNOWN_APPS
    gecko_apps = {v: k for k, v in KNOWN_APPS.iteritems()}
  appID = params.get("appID", ["unknown"])[0]

  application = gecko_apps.get(appID, "unknown")
  applicationVersion = params.get("appVersion", ["unknown"])[0]

  # Only leave the major and minor release number for application
  applicationVersion = re.sub(r"^(\d+\.\d+).*", r"\1", applicationVersion)

  return version, application, applicationVersion

def parse_chrome_query(query):
  params = urlparse.parse_qs(query)

  if params.get("prod", ["unknown"])[0] in ("chromecrx", "chromiumcrx"):
    application = "chrome"
  else:
    application = "unknown"
  applicationVersion = params.get("prodversion", ["unknown"])[0]

  params2 = urlparse.parse_qs(params.get("x", [""])[0])
  version = params2.get("v", ["unknown"])[0]

  # Only leave the major and minor release number for application
  applicationVersion = re.sub(r"^(\d+\.\d+).*", r"\1", applicationVersion)

  return version, application, applicationVersion

def parse_update_flag(query):
  return "update" if query == "update" else "install"

def parse_record(line, ignored, geo, geov6):
  global log_regexp, mirror_name
  if log_regexp == None:
    log_regexp = re.compile(r'(\S+) \S+ \S+ \[([^]\s]+) ([+\-]\d\d)(\d\d)\] "GET ([^"\s]+) [^"]+" (\d+) (\d+) "[^"]*" "([^"]*)"(?: "[^"]*" \S+ "[^"]*" "[^"]*" "([^"]*)")?')
  if mirror_name == None:
    mirror_name = re.sub(r"\..*", "", socket.gethostname())

  match = re.search(log_regexp, line)
  if not match:
    return None

  status = int(match.group(6))
  if status != 200:
    return None

  info = {
    "mirror": mirror_name,
    "size": int(match.group(7)),
  }

  info["ip"], info["country"] = process_ip(match.group(1), geo, geov6)
  info["time"], info["month"], info["day"], info["weekday"], info["hour"] = parse_time(match.group(2), int(match.group(3)), int(match.group(4)))
  info["file"], info["query"] = parse_path(match.group(5))
  info["ua"], info["uaversion"] = parse_ua(match.group(8))
  info["fullua"] = "%s %s" % (info["ua"], info["uaversion"])
  info["clientid"] = match.group(9)

  # Additional metadata depends on file type
  filename = os.path.basename(info["file"])
  ext = os.path.splitext(filename)[1]
  if ext == ".txt" or filename == "update.json" or filename == "notification.json":
    # Subscription downloads, libadblockplus update checks and notification
    # checks are performed by the downloader
    parse_downloader_query(info)
  elif ext == ".tpl":
    # MSIE TPL download, no additional data here
    pass
  elif ext in (".xpi", ".crx", ".apk", ".msi", ".exe"):
    # Package download, might be an update
    info["installType"] = parse_update_flag(info["query"])
  elif filename == "update.rdf":
    # Gecko update check or a legacy Android update check. The latter doesn't
    # have usable data anyway so trying the Chrome route won't do any harm.
    info["addonName"] = parse_addon_name(info["file"])
    info["addonVersion"], info["application"], info["applicationVersion"] = parse_gecko_query(info["query"])
  elif filename == "updates.xml":
    # Chrome update check
    info["addonName"] = parse_addon_name(info["file"])
    info["addonVersion"], info["application"], info["applicationVersion"] = parse_chrome_query(info["query"])
  else:
    ignored.add(info["file"])
    return None

  if "addonName" in info:
    info["fullAddon"] = "%s %s" % (info["addonName"], info["addonVersion"])
  if "application" in info:
    info["fullApplication"] = "%s %s" % (info["application"], info["applicationVersion"])
  if "platform" in info:
    info["fullPlatform"] = "%s %s" % (info["platform"], info["platformVersion"])
  return info

def add_record(info, section, ignore_fields=()):
  section["hits"] = section.get("hits", 0) + 1
  section["bandwidth"] = section.get("bandwidth", 0) + info["size"]

  if len(ignore_fields) < 2:
    for field in map(lambda f: f["name"], common.fields):
      if field in ignore_fields or field not in info:
        continue

      value = info[field]
      if field not in section:
        section[field] = {}
      if value not in section[field]:
        section[field][value] = {}

      add_record(info, section[field][value], ignore_fields + (field,))

def parse_stdin(geo, geov6, verbose):
  data = {}
  ignored = set()
  for line in sys.stdin:
    info = parse_record(line, ignored, geo, geov6)
    if info == None:
      continue

    if info["month"] not in data:
      data[info["month"]] = {}
    section = data[info["month"]]

    if info["file"] not in section:
      section[info["file"]] = {}
    section = section[info["file"]]

    add_record(info, section)

  if verbose:
    print "Ignored files"
    print "============="
    print "\n".join(sorted(ignored))
  return data

if __name__ == "__main__":
  setupStderr()

  verbose = (len(sys.argv) >= 2 and sys.argv[1] == "verbose")
  geo = pygeoip.GeoIP(get_config().get("stats", "geoip_db"), pygeoip.MEMORY_CACHE)
  geov6 = pygeoip.GeoIP(get_config().get("stats", "geoipv6_db"), pygeoip.MEMORY_CACHE)
  result = parse_stdin(geo, geov6, verbose)

  with codecs.open(get_config().get("stats", "tempFile"), "wb", encoding="utf-8") as file:
    json.dump(result, file, indent=2, sort_keys=True)
