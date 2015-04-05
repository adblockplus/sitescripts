# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
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

import codecs
import os
import re
import subprocess
import tarfile
import traceback
from StringIO import StringIO

from sitescripts.utils import get_config

def _parse_targetspec(value, name):
  target = {}
  for spec in value.split():
    known = False
    for parameter in ("extension", "application", "platform"):
      if spec.startswith(parameter + "="):
        target[parameter] = spec[len(parameter + "="):]
        known = True
      elif spec.startswith(parameter + "Version>="):
        target[parameter + "MinVersion"] = spec[len(parameter + "Version>="):]
        known = True
      elif spec.startswith(parameter + "Version<="):
        target[parameter + "MaxVersion"] = spec[len(parameter + "Version<="):]
        known = True
      elif spec.startswith(parameter + "Version="):
        target[parameter + "MinVersion"] = target[parameter + "MaxVersion"] = spec[len(parameter + "Version="):]
        known = True
    if not known:
      raise Exception("Unknown target specifier '%s' in file '%s'" % (spec, name))
  return target

def _parse_notification(data, name):
  notification = {"id": name, "severity": "information", "message": {}, "title": {}}

  for line in data:
    if not re.search(r"\S", line):
      continue

    if line.find("=") < 0:
      raise Exception("Could not process line '%s' in file '%s'" % (line.strip(), name))

    key, value = map(unicode.strip, line.split("=", 1))

    if key == "inactive":
      notification["inactive"] = True
    elif key == "severity":
      if value not in ("information", "critical"):
        raise Exception("Unknown severity value '%s' in file '%s'" % (value, name))
      notification["severity"] = value
    elif key == "links":
      notification["links"] = value.split()
    elif key.startswith("title."):
      locale = key[len("title."):]
      notification["title"][locale] = value
    elif key.startswith("message."):
      locale = key[len("message."):]
      notification["message"][locale] = value
    elif key == "target":
      target = _parse_targetspec(value, name)
      if "targets" in notification:
        notification["targets"].append(target)
      else:
        notification["targets"] = [target]
    else:
      raise Exception("Unknown parameter '%s' in file '%s'" % (key, name))

  if "en-US" not in notification["title"]:
    raise Exception("No title for en-US (default language) in file '%s'" % name)
  if "en-US" not in notification["message"]:
    raise Exception("No message for en-US (default language) in file '%s'" % name)
  return notification

def load_notifications():
  repo = get_config().get("notifications", "repository")
  subprocess.call(["hg", "-R", repo, "pull", "-q"])
  command = ["hg", "-R", repo, "archive", "-r", "default", "-t", "tar",
      "-p", ".", "-X", os.path.join(repo, ".hg_archival.txt"), "-"]
  data = subprocess.check_output(command)

  notifications = []
  with tarfile.open(mode="r:", fileobj=StringIO(data)) as archive:
    for fileinfo in archive:
      name = fileinfo.name
      if name.startswith("./"):
        name = name[2:]

      if fileinfo.type == tarfile.REGTYPE:
        data = codecs.getreader("utf8")(archive.extractfile(fileinfo))
        try:
          notification = _parse_notification(data, name)
          if "inactive" in notification:
            continue
          notifications.append(notification)
        except:
          traceback.print_exc()
  return notifications
