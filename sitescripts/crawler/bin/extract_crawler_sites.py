#!/usr/bin/env python
# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import os, re, subprocess

def hg(args):
  return subprocess.Popen(["hg"] + args, stdout = subprocess.PIPE)

def update_filter_list(filter_list):
  if os.path.isdir(filter_list):
    hg(["pull", "--cwd", filter_list]).communicate()
    hg(["update", "--cwd", filter_list]).communicate()
  else:
    url = "https://hg.adblockplus.org/" + filter_list
    hg(["clone", url, filter_list]).communicate()

def extract_urls():
  process = hg(["log", "--template", "{desc}\n"])

  while True:
    line = process.stdout.readline()
    if line == "":
      break

    matches = re.match(r"[A-Z]:.*(https?://.*)", line)
    if not matches:
      continue

    url = matches.group(1).strip()
    print "INSERT INTO crawler_sites (url) VALUES ('" + url + "');"

if __name__ == "__main__":
  update_filter_list("easylist")
  os.chdir("easylist")
  extract_urls()
