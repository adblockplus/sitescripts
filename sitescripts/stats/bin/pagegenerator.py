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

import os, re, codecs, simplejson, time, itertools
from datetime import date
from sitescripts.utils import get_config, setupStderr, get_custom_template_environment, cached
import sitescripts.stats.common as common
from sitescripts.stats.countrycodes import countrycodes

@cached(float("inf"))
def get_template_environment():
  return get_custom_template_environment({
    "monthname": lambda value: date(int(value[0:4]), int(value[4:]), 1).strftime("%b %Y"),
    "weekday": lambda value: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][int(value)],
    "countryname": lambda value: countrycodes.get(value, "Unknown"),
    "sortfield": lambda value, field: (field["sort"] if "sort" in field else default_sort)(value),
    "maxhits": lambda items: max(itertools.chain((value["hits"] for key, value in items), [1])),
    "maxbandwidth": lambda items: max(itertools.chain((value["bandwidth"] for key, value in items), [1])),
    "sumhits": lambda items: max(sum(value["hits"] for key, value in items), 1),
    "sumbandwidth": lambda items: max(sum(value["bandwidth"] for key, value in items), 1),
    "isspecial": lambda name, field: field["isspecial"](name) if "isspecial" in field else False,
  })

@cached(float("inf"))
def get_main_page_template():
  return get_template_environment().get_template(get_config().get("stats", "mainPageTemplate"))

@cached(float("inf"))
def get_file_stats_template():
  return get_template_environment().get_template(get_config().get("stats", "filePageTemplate"))

@cached(float("inf"))
def get_file_overview_template():
  return get_template_environment().get_template(get_config().get("stats", "fileOverviewTemplate"))

def default_sort(obj):
  return sorted(obj.items(), key=lambda (k,v): v["hits"], reverse=True)

def ensure_dir(path):
  dir = os.path.dirname(path)
  if not os.path.exists(dir):
    os.makedirs(dir)

def generate_main_page(outputfile, month, url, data):
  ensure_dir(outputfile)
  get_main_page_template().stream({
    "now": time.time(),
    "month": month,
    "url": url,
    "data": data,
  }).dump(outputfile)

def generate_file_stats(outputfile, month, url, overview_url, data, filter=None, filtered_urls={}):
  ensure_dir(outputfile)
  get_file_stats_template().stream({
    "now": time.time(),
    "month": month,
    "url": url,
    "overview_url": overview_url,
    "data": data,
    "fields": common.fields,
    "filter": filter,
    "filtered_urls": filtered_urls
  }).dump(outputfile)

def generate_file_overview(outputfile, url, data):
  ensure_dir(outputfile)
  get_file_overview_template().stream({
    "now": time.time(),
    "url": url,
    "data": data
  }).dump(outputfile)

def get_names(dir, needdirectories):
  for file in os.listdir(dir):
    path = os.path.join(dir, file)
    if (needdirectories and os.path.isdir(path)) or (not needdirectories and os.path.isfile(path)):
      yield common.filename_decode(file), path

def generate_pages(datadir, outputdir):
  for server_type, server_type_dir in get_names(datadir, True):
    baseURL = get_config().get("stats", "baseURL_" + server_type)
    filedata = {}
    current_month = None
    for month, month_dir in get_names(server_type_dir, True):
      if current_month == None or month > current_month:
        current_month = month

      for filename, path in get_names(month_dir, False):
        filename = re.sub(r"\.json$", "", filename)
        with codecs.open(path, "rb", encoding="utf-8") as file:
          data = simplejson.load(file)

        overview_url = "../../overview-" + common.filename_encode(filename + ".html")
        filtered_urls = {}
        for field in common.fields:
          if field["name"] not in data:
            continue
          # Create filtered views for the first thirty values of a field if they
          # have filtered data.
          for name, value in get_template_environment().filters["sortfield"](data[field["name"]], field)[0:30]:
            if filter(lambda k: k not in ("hits", "bandwidth"), value.keys()):
              outputfile = os.path.join(outputdir,
                  common.filename_encode(server_type),
                  common.filename_encode(month),
                  common.filename_encode(filename),
                  "filtered-%s-%s.html" % (
                    common.filename_encode(field["name"]),
                    common.filename_encode(name),
                  ))
              generate_file_stats(outputfile, month, baseURL + filename, overview_url,
                  value, filter={"field": field, "value": name})

              if not field["name"] in filtered_urls:
                filtered_urls[field["name"]] = {}
              filtered_urls[field["name"]][name] = os.path.basename(outputfile)

        outputfile = os.path.join(outputdir,
            common.filename_encode(server_type),
            common.filename_encode(month),
            common.filename_encode(filename),
            "index.html")
        generate_file_stats(outputfile, month, baseURL + filename, overview_url,
            data, filtered_urls=filtered_urls)

        if filename not in filedata:
          filedata[filename] = {}
        month_url = (common.filename_encode(month) + "/" +
                     common.filename_encode(filename) + "/" +
                     "index.html")
        filedata[filename][month] = {"url": month_url, "hits": data["hits"], "bandwidth": data["bandwidth"]}

    monthdata = {}
    for filename, data in filedata.iteritems():
      outputfile = os.path.join(outputdir,
          common.filename_encode(server_type),
          "overview-" + common.filename_encode(filename + ".html"))
      generate_file_overview(outputfile, baseURL + filename, data)

      if current_month in data:
        monthdata[filename] = dict(data[current_month])

    outputfile = os.path.join(outputdir, common.filename_encode(server_type), "index.html")
    generate_main_page(outputfile, current_month, baseURL, monthdata)

if __name__ == '__main__':
  setupStderr()

  datadir = get_config().get("stats", "dataDirectory")
  outputdir = get_config().get("stats", "outputDirectory")
  generate_pages(datadir, outputdir)
