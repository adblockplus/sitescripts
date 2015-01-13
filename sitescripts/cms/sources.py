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

import sys, os, subprocess, zipfile, json, urlparse, codecs
from StringIO import StringIO
from ConfigParser import SafeConfigParser

class Source:
  def resolve_link(self, url, locale):
    parsed = urlparse.urlparse(url)
    page = parsed.path
    if parsed.scheme != "" or page.startswith("/") or page.startswith("."):
      # Not a page link
      return None, None

    if parsed.path == "" and url != "":
      # Page-relative link
      return None, None

    config = self.read_config()
    default_locale = config.get("general", "defaultlocale")
    default_page = config.get("general", "defaultpage")

    checked_page = page
    if config.has_option("locale_overrides", page):
      checked_page = config.get("locale_overrides", page)

    if self.has_localizable_file(default_locale, checked_page):
      if not self.has_localizable_file(locale, checked_page):
        locale = default_locale
    elif self.has_locale(default_locale, checked_page):
      if not self.has_locale(locale, checked_page):
        locale = default_locale
    else:
      print >>sys.stderr, "Warning: Link to %s cannot be resolved" % page

    if page == default_page:
      page = ""

    path = "/%s/%s" % (locale, page)
    return locale, urlparse.urlunparse(parsed[0:2] + (path,) + parsed[3:])

  def read_config(self):
    configdata = self.read_file("settings.ini")
    config = SafeConfigParser()
    config.readfp(StringIO(configdata))
    return config

  #
  # Page helpers
  #

  @staticmethod
  def page_filename(page, format):
    return "pages/%s.%s" % (page, format)

  def list_pages(self):
    for filename in self.list_files("pages"):
      root, ext = os.path.splitext(filename)
      format = ext[1:].lower()
      yield root, format

  def has_page(self, page, format):
    return self.has_file(self.page_filename(page, format))

  def read_page(self, page, format):
    return self.read_file(self.page_filename(page, format))

  #
  # Localizable files helpers
  #

  @staticmethod
  def localizable_file_filename(locale, filename):
    return "locales/%s/%s" % (locale, filename)

  def list_localizable_files(self):
    default_locale = self.read_config().get("general", "defaultlocale")
    return filter(
      lambda f: os.path.splitext(f)[1].lower() != ".json",
      self.list_files("locales/%s" % default_locale)
    )

  def has_localizable_file(self, locale, filename):
    return self.has_file(self.localizable_file_filename(locale, filename))

  def read_localizable_file(self, locale, filename):
    return self.read_file(self.localizable_file_filename(locale, filename), binary=True)

  #
  # Static file helpers
  #

  @staticmethod
  def static_filename(filename):
    return "static/%s" % filename

  def list_static(self):
    return self.list_files("static")

  def has_static(self, filename):
    return self.has_file(self.static_filename(filename))

  def read_static(self, filename):
    return self.read_file(self.static_filename(filename), binary=True)

  #
  # Locale helpers
  #

  @classmethod
  def locale_filename(cls, locale, page):
    return cls.localizable_file_filename(locale, page + ".json")

  def list_locales(self):
    result = set()
    for filename in self.list_files("locales"):
      if "/" in filename:
        locale, path = filename.split("/", 1)
        result.add(locale)
    return result

  def has_locale(self, locale, page):
    config = self.read_config()
    if config.has_option("locale_overrides", page):
      page = config.get("locale_overrides", page)
    return self.has_file(self.locale_filename(locale, page))

  def read_locale(self, locale, page):
    default_locale = self.read_config().get("general", "defaultlocale")
    if locale == default_locale:
      result = {}
    else:
      result = self.read_locale(default_locale, page)

    if self.has_locale(locale, page):
      filedata = self.read_file(self.locale_filename(locale, page))
      localedata = json.loads(filedata)
      for key, value in localedata.iteritems():
        result[key] = value["message"]

    return result

  #
  # Template helpers
  #

  @staticmethod
  def template_filename(template):
    return "templates/%s.tmpl" % template

  def read_template(self, template):
    return self.read_file(self.template_filename(template))

  #
  # Include helpers
  #

  @staticmethod
  def include_filename(include, format):
    return "includes/%s.%s" % (include, format)

  def has_include(self, include, format):
    return self.has_file(self.include_filename(include, format))

  def read_include(self, include, format):
    return self.read_file(self.include_filename(include, format))

class MercurialSource(Source):
  def __init__(self, repo):
    command = ["hg", "-R", repo, "archive", "-r", "default",
        "-t", "uzip", "-p", ".", "-"]
    data = subprocess.check_output(command)
    self._archive = zipfile.ZipFile(StringIO(data), mode="r")

    command = ["hg", "-R", repo, "id", "-n", "-r", "default"]
    self.version = subprocess.check_output(command).strip()

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    self.close()
    return False

  def close(self):
    self._archive.close()

  def has_file(self, filename):
    try:
      self._archive.getinfo("./%s" % filename)
    except KeyError:
      return False
    return True

  def read_file(self, filename, binary=False):
    result = self._archive.read("./%s" % filename)
    if not binary:
      result = result.decode("utf-8")
    return result

  def list_files(self, subdir):
    prefix = "./%s/" % subdir
    for filename in self._archive.namelist():
      if filename.startswith(prefix):
        yield filename[len(prefix):]

class FileSource(Source):
  def __init__(self, dir):
    self._dir = dir

  def __enter__(self):
    return self

  def __exit__(self, type, value, traceback):
    return False

  def close(self):
    pass

  def get_path(self, filename):
    return os.path.join(self._dir, *filename.split("/"))

  def has_file(self, filename):
    return os.path.isfile(self.get_path(filename))

  def read_file(self, filename, binary=False):
    encoding = None if binary else "utf-8"
    with codecs.open(self.get_path(filename), "rb", encoding=encoding) as handle:
      return handle.read()

  def list_files(self, subdir):
    result = []
    def do_list(dir, relpath):
      try:
        files = os.listdir(dir)
      except OSError:
        return

      for filename in files:
        path = os.path.join(dir, filename)
        if os.path.isfile(path):
          result.append(relpath + filename)
        elif os.path.isdir(path):
          do_list(path, relpath + filename + "/")
    do_list(self.get_path(subdir), "")
    return result
