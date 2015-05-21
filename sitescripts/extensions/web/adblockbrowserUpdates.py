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

import hashlib
import os
import re
from urlparse import parse_qs

from jinja2 import Template

from sitescripts.utils import get_config
from sitescripts.web import url_handler

_MANIFEST_TEMPLATE = Template("""<?xml version="1.0"?>
<updates>
{% if build %}
    <update buildID="{{ build.build_id }}">
        <patch
          URL="{{ build.url }}"
          hashFunction="{{ build.hash_function }}"
          hashValue="{{ build.hash_value }}"
          size="{{ build.size }}"/>
    </update>
{% endif %}
</updates>

""", autoescape=True)

def _get_latest_build(builds_dir):
  latest_build = {"id": 0}
  for file in os.listdir(builds_dir):
    match = re.search(r"^adblockbrowser-.*?(\d+)-\w+\.apk$", file)
    if match:
      build_id = int(match.group(1))
      if build_id > latest_build["id"]:
        latest_build["id"] = build_id
        latest_build["path"] = os.path.join(builds_dir, file)
  if latest_build["id"] == 0:
    return {}
  return latest_build

def _render_manifest(build=None):
  if not build:
    return _MANIFEST_TEMPLATE.render()

  nightlies_url = get_config().get("extensions", "nightliesURL")
  build_url = "%s/adblockbrowser/%s?update" % (nightlies_url.rstrip("/"),
                                               os.path.basename(build["path"]))
  with open(build["path"], "rb") as build_file:
    build_content = build_file.read()
  return _MANIFEST_TEMPLATE.render({
    "build": {
      "build_id": build["id"],
      "url": build_url,
      "hash_function": "SHA512",
      "hash_value": hashlib.sha512(build_content).hexdigest(),
      "size": len(build_content)
    }
  })

def _get_update_manifest(current_build_id):
  nightlies_dir = get_config().get("extensions", "nightliesDirectory")
  builds_dir = os.path.join(nightlies_dir, "adblockbrowser")
  if not os.path.isdir(builds_dir):
    return _render_manifest()

  latest_build = _get_latest_build(builds_dir)
  if not latest_build or current_build_id >= latest_build["id"]:
    return _render_manifest()
  return _render_manifest(latest_build)

@url_handler("/devbuilds/adblockbrowser/updates.xml")
def adblockbrowser_updates(environ, start_response):
  params = parse_qs(environ.get("QUERY_STRING", ""))
  try:
    version = params.get("addonVersion", [""])[0]
    build_id = int(re.search(r"(\d+)$", version).group(1))
  except:
    start_response("400 Processing Error", [("Content-Type", "text/plain")])
    return ["Failed to parse addonVersion."]
  manifest = _get_update_manifest(build_id)
  response = manifest.encode("utf-8")
  start_response("200 OK", [("Content-Type", "application/xml; charset=utf-8")])
  return [response]
