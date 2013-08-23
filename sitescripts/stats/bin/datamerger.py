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

import os, sys, re, codecs, subprocess, urllib, simplejson, traceback
import sitescripts.stats.common as common
from sitescripts.utils import get_config, setupStderr

def read_stats_file(path):
  match = re.search(r"^ssh://(\w+)@([^/:]+)(?::(\d+))?", path)
  if match:
    command = ["ssh", "-q", "-o", "NumberOfPasswordPrompts 0", "-T", "-k", "-l", match.group(1), match.group(2)]
    if match.group(3):
      command[1:1] = ["-P", match.group(3)]
    data = subprocess.check_output(command)
    return simplejson.loads(data.decode("utf-8"))
  elif path.startswith("http://") or path.startswith("https://"):
    return simplejson.load(urllib.urlopen(path).read().decode("utf-8"))
  elif os.path.exists(path):
    with codecs.open(path, "rb", encoding="utf-8") as file:
      return simplejson.load(file)

  raise IOError("Path '%s' not recognized" % path)

def get_stats_files(mirrors):
  config = get_config()

  if len(mirrors) > 0:
    options = map(lambda m: "mirror_" + m, mirrors)
  else:
    options = filter(lambda o: o.startswith("mirror_"), config.options("stats"))
  for option in options:
    if config.has_option("stats", option):
      value = config.get("stats", option)
      if " " in value:
        yield re.split(r"\s+", value, 1)
      else:
        print >>sys.stderr, "Option '%s' has invalid value: '%s'" % (option, value)
    else:
      print >>sys.stderr, "Option '%s' not found in the configuration" % option

def merge_objects(object1, object2):
  for key, value in object2.iteritems():
    if key in object1:
      if isinstance(value, int):
        object1[key] += value
      else:
        merge_objects(object1[key], object2[key])
    else:
      object1[key] = value

def merge_stats_file(server_type, data):
  base_dir = os.path.join(get_config().get("stats", "dataDirectory"), common.filename_encode(server_type))
  for month, month_data in data.iteritems():
    for name, file_data in month_data.iteritems():
      path = os.path.join(base_dir, common.filename_encode(month), common.filename_encode(name + ".json"))
      if os.path.exists(path):
        with codecs.open(path, "rb", encoding="utf-8") as file:
          existing = simplejson.load(file)
      else:
        existing = {}

      merge_objects(existing, file_data)

      dir = os.path.dirname(path)
      if not os.path.exists(dir):
        os.makedirs(dir)

      with codecs.open(path, "wb", encoding="utf-8") as file:
        simplejson.dump(existing, file, indent=2, sort_keys=True)

def merge_mirror_stats(mirrors):
  for server_type, path in get_stats_files(mirrors):
    try:
      merge_stats_file(server_type, read_stats_file(path))
    except:
      print >>sys.stderr, "Unable to merge stats for '%s'" % path
      traceback.print_exc()

if __name__ == "__main__":
  setupStderr()
  merge_mirror_stats(sys.argv[1:])
