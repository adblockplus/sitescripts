# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import MySQLdb, os, re, sys
from sitescripts.utils import get_config

def parse_hide_filter(line):
  match = re.search(r"^(.*?)##", line)
  return {line: match.group(1)} if match else {}

def parse_block_filter(line):
  match = re.search(r"domain=(.*)", line)
  if match:
    domains = match.group(1).split("|")
    filters = {}
    for domain in domains:
      filters[line] = domain;
    return filters

  match = re.search(r"^\|\|(.*?)[/\^]", line)
  return {line: match.group(1)} if match else {}

def remove_comment(line):
  exclamation_index = line.find("!")
  if exclamation_index != -1:
    return line[:exclamation_index]
  return line

def extract_filters(filter_list_dir, domain_filter_files):
  filters = {}

  for filter_file in domain_filter_files:
    is_hide_file = "hide" in filter_file
    parse_filter = parse_hide_filter if is_hide_file else parse_block_filter
    file_path = filter_list_dir + "/" + filter_file

    try:
      for line in open(file_path):
        line = line.strip()
        line = remove_comment(line)
        filters.update(parse_filter(line))
    except IOError:
      print >>sys.stderr, "Unable to read filters from '%s'" % file_path

  return filters

def print_statements(filters):
  query = "INSERT INTO crawler_filters (filter, domain) VALUES ('%s', '%s');"
  for filter_line, domain in filters.iteritems():
    escaped_filter = MySQLdb.escape_string(filter_line)
    escaped_domain = MySQLdb.escape_string(domain)
    print query % (escaped_filter, escaped_domain)

if __name__ == "__main__":
  config = get_config()
  filter_list_dir = config.get("crawler", "filter_list_repository")
  domain_filter_files = config.get("crawler", "domain_specific_filter_files")
  domain_filter_file_list = re.split(r"\s*,\s*", domain_filter_files)
  filters = extract_filters(filter_list_dir, domain_filter_file_list)
  print_statements(filters)
