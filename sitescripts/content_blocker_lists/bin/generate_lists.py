#!/usr/bin/env python
# coding: utf-8

# This file is part of Adblock Plus <https://adblockplus.org/>,
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

import os
import subprocess
import urllib2

from sitescripts.utils import get_config

def _update_abp2blocklist():
  with open(os.devnull, "w") as devnull:
    config = get_config()
    abp2blocklist_path = config.get("content_blocker_lists",
                                    "abp2blocklist_path")
    if os.path.isdir(abp2blocklist_path):
        subprocess.check_call(("hg", "pull", "-u", "-R", abp2blocklist_path),
                              stdout=devnull)
    else:
      abp2blocklist_url = config.get("content_blocker_lists",
                                     "abp2blocklist_url")
      subprocess.check_call(("hg", "clone", abp2blocklist_url,
                             abp2blocklist_path), stdout=devnull)
    subprocess.check_call(("npm", "install"), cwd=abp2blocklist_path,
                          stdout=devnull)

def _download(url_key):
  url = get_config().get("content_blocker_lists", url_key)
  response = urllib2.urlopen(url)
  try:
    return response.read()
  finally:
    response.close()

def _convert_filter_list(sources, destination_path_key):
  config = get_config()
  destination_path = config.get("content_blocker_lists", destination_path_key)
  with open(destination_path, "wb") as destination_file:
    abp2blocklist_path = config.get("content_blocker_lists",
                                    "abp2blocklist_path")
    process = subprocess.Popen(("node", "abp2blocklist.js"),
                               cwd=abp2blocklist_path, stdin=subprocess.PIPE,
                               stdout=destination_file)
    try:
      for source in sources:
        print >>process.stdin, source
    finally:
      process.stdin.close()
      process.wait()

  if process.returncode:
    raise Exception("abp2blocklist returned %s" % process.returncode)

if __name__ == "__main__":
  _update_abp2blocklist()

  easylist = _download("easylist_url")
  exceptionrules = _download("exceptionrules_url")

  _convert_filter_list([easylist], "easylist_content_blocker_path")
  _convert_filter_list([easylist, exceptionrules],
                       "combined_content_blocker_path")
