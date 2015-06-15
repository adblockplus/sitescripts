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

import copy
import json
import random
import time
import urlparse

from sitescripts.notifications.parser import load_notifications
from sitescripts.web import url_handler

def _determine_groups(version, notifications):
  version_groups = dict(x.split("/") for x in version.split("-")[1:]
                        if x.count("/") == 1)
  groups = []
  for notification in notifications:
    if "variants" not in notification:
      continue
    group_id = notification["id"]
    if group_id in version_groups:
      groups.append({"id": group_id, "variant": int(version_groups[group_id])})
  return groups

def _assign_groups(notifications):
  groups = []
  selection = random.random()
  start = 0
  for notification in notifications:
    if "variants" not in notification:
      continue
    group = {"id": notification["id"], "variant": 0}
    groups.append(group)
    for i, variant in enumerate(notification["variants"]):
      sample_size = variant["sample"]
      end = start + sample_size
      selected = sample_size > 0 and start <= selection <= end
      start = end
      if selected:
        group["variant"] = i + 1
        break
  return groups

def _get_active_variant(notifications, groups):
  for group in groups:
    group_id = group["id"]
    variant = group["variant"]
    if variant == 0:
      continue
    notification = next(x for x in notifications if x["id"] == group_id)
    notification = copy.deepcopy(notification)
    notification.update(notification["variants"][variant - 1])
    for key_to_remove in ("sample", "variants"):
      notification.pop(key_to_remove, None)
    return notification

def _generate_version(groups):
  version = time.strftime("%Y%m%d%H%M", time.gmtime())
  for group in groups:
    version += "-%s/%s" % (group["id"], group["variant"])
  return version

def _create_response(notifications, groups):
  active_variant = _get_active_variant(notifications, groups)
  if active_variant:
    notifications = [active_variant]
  else:
    notifications = [x for x in notifications if "variants" not in x]
  response = {
    "version": _generate_version(groups),
    "notifications": notifications
  }
  return response

@url_handler("/notification.json")
def notification(environ, start_response):
  params = urlparse.parse_qs(environ.get("QUERY_STRING", ""))
  version = params.get("lastVersion", [""])[0]
  notifications = load_notifications()
  groups = _determine_groups(version, notifications)
  if not groups:
    groups = _assign_groups(notifications)
  response = _create_response(notifications, groups)
  response_headers = [("Content-Type", "application/json; charset=utf-8"),
                      ("ABP-Notification-Version", response["version"])]
  response_body = json.dumps(response, ensure_ascii=False, indent=2,
                             separators=(",", ": "),
                             sort_keys=True).encode("utf-8")
  start_response("200 OK", response_headers)
  return response_body
