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

from .converters import converters, TemplateConverter

def process_page(source, locale, page, format, site_url_override=None):
  params = {
    "source": source,
    "template": "default",
    "locale": locale,
    "title": "title",
    "page": page,
    "pagedata": source.read_page(page, format),
    "config": source.read_config(),
  }

  localefile = page
  if params["config"].has_option("locale_overrides", page):
    localefile = params["config"].get("locale_overrides", page)
  params["localedata"] = source.read_locale(params["locale"], localefile)

  if params["config"].has_option("general", "siteurl"):
    if site_url_override:
      params["site_url"] = site_url_override
    else:
      params["site_url"] = params["config"].get("general", "siteurl")

  try:
    converter = converters[format](params)
  except KeyError:
    raise Exception("Page %s uses unknown format %s" % (page, format))

  # Note: The converter might change some parameters so we can only read in
  # template data here.
  params["templatedata"] = source.read_template(params["template"])
  template_converter = TemplateConverter(params, key="templatedata")

  params["available_locales"] = sorted(
    filter(
      lambda locale: source.has_locale(locale, localefile),
      source.list_locales()
    )
  )

  params["head"], params["body"] = converter()
  return template_converter()
