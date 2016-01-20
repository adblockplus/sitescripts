# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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

import re
import hashlib

def filename_encode(name):
  """
    This encodes any string to a valid file name while ensuring that the
    original string can still be reconstructed. All characters except 0-9, A-Z,
    the period and underscore are encoded as "-12cd" where "12cd" stands for the
    hexadecimal representation of the character's ordinal. File names longer
    than 150 characters will be still be unique but no longer reversible due to
    file system limitations.
  """
  result = re.sub(r"[^\w\.]", lambda match: "-%04x" % ord(match.group(0)), name)
  if len(result) > 150:
    result = result[:150] + "--%s" % hashlib.md5(result[150:]).hexdigest()
  return result

def filename_decode(path):
  """
    This reconstructs a string encoded with filename_encode().
  """
  path = re.sub(r"--[0-9A-Fa-f]{32}", u"\u2026", path)
  path = re.sub(r"-([0-9a-f]{4})", lambda match: unichr(int(match.group(1), 16)), path)
  return path

basic_fields = [
  {
    "name": "day",
    "title": "Days of month",
    "coltitle": "Day",
    "showaverage": True,
    "defaultcount": 31,
    "sort": lambda obj: sorted(obj.items(), key=lambda (k,v): int(k)),
  },
  {
    "name": "weekday",
    "title": "Days of week",
    "coltitle": "Weekday",
    "showaverage": True,
    "sort": lambda obj: sorted(obj.items(), key=lambda (k,v): int(k)),
    "isspecial": lambda weekday: weekday == 5 or weekday == 6,
  },
  {
    "name": "hour",
    "title": "Hours of day",
    "coltitle": "Hour",
    "showaverage": True,
    "sort": lambda obj: sorted(obj.items(), key=lambda (k,v): int(k)),
  },
  {
    "name": "country",
    "title": "Countries",
    "coltitle": "Country",
  },
  {
    "name": "ua",
    "title": "Browsers",
    "coltitle": "Browser",
  },
  {
    "name": "fullua",
    "title": "Browser versions",
    "coltitle": "Browser version",
  },
  {
    "name": "referrer",
    "title": "Referrers",
    "coltitle": "Referrer",
  },
  {
    "name": "status",
    "title": "Status codes",
    "coltitle": "Status code",
  },
  {
    "name": "mirror",
    "title": "Download mirrors",
    "coltitle": "Download mirror",
  },
]

downloader_fields = [
  {
    "name": "addonName",
    "title": "Extensions",
    "coltitle": "Extension",
  },
  {
    "name": "fullAddon",
    "title": "Extension versions",
    "coltitle": "Extension version",
  },
  {
    "name": "application",
    "title": "Host applications",
    "coltitle": "Host application",
  },
  {
    "name": "fullApplication",
    "title": "Host application versions",
    "coltitle": "Host application version",
  },
  {
    "name": "platform",
    "title": "Platforms",
    "coltitle": "Platform",
  },
  {
    "name": "fullPlatform",
    "title": "Platform versions",
    "coltitle": "Platform version",
  },
  {
    "name": "downloadInterval",
    "title": "Download intervals",
    "coltitle": "Download interval",
  },
  {
    "name": "previousDownload",
    "hidden": True,
  },
  {
    "name": "firstDownload",
    "title": "Initial download",
    "filter": True,
  },
  {
    "name": "firstInDay",
    "title": "First download this day",
    "filter": True,
  },
  {
    "name": "firstInWeek",
    "title": "First download this week",
    "filter": True,
  },
  {
    "name": "firstInMonth",
    "title": "First download this month",
    "filter": True,
  },
]

install_fields = [
  {
    "name": "installType",
    "title": "Install types",
    "coltitle": "Install type",
  },
]


fields = basic_fields + downloader_fields + install_fields
