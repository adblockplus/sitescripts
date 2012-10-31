# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2012 Eyeo GmbH
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

import MySQLdb, os, re, subprocess
from sitescripts.utils import get_config

def hg(args):
  return subprocess.Popen(["hg"] + args, stdout = subprocess.PIPE)

def extract_urls(filter_list_dir):
  os.chdir(filter_list_dir)
  process = hg(["log", "--template", "{desc}\n"])
  urls = set([])

  for line in process.stdout:
    match = re.search(r"\b(https?://\S*)", line)
    if not match:
      continue

    url = match.group(1).strip()
    urls.add(url)

  return urls

def print_statements(urls):
  for url in urls:
    escaped_url = MySQLdb.escape_string(url)
    print "INSERT INTO crawler_sites (url) VALUES ('" + escaped_url + "');"

if __name__ == "__main__":
  filter_list_dir = get_config().get("crawler", "filter_list_repository")
  urls = extract_urls(filter_list_dir)
  print_statements(urls)
