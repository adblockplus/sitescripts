# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import MySQLdb, os, re, subprocess
from sitescripts.utils import get_config

def hg(args):
  return subprocess.Popen(["hg"] + args, stdout = subprocess.PIPE)

def extract_urls(filter_list_dir):
  os.chdir(filter_list_dir)
  process = hg(["log", "--template", "{desc}\n"])
  urls = set([])

  for line in process.stdout:
    matches = re.match(r"[A-Z]:.*(https?://\S*)", line)
    if not matches:
      continue

    url = matches.group(1).strip()
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
