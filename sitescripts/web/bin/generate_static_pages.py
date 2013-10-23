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

import sys, os, re, errno, codecs
from ...utils import setupStderr, cached
from ..utils import process_page
from ..sources import MercurialSource

def generate_pages(repo, output_dir):
  known_files = set()

  def write_file(path_parts, contents, binary=False):
    encoding = None if binary else "utf-8"
    outfile = os.path.join(output_dir, *path_parts)
    if outfile in known_files:
      print >>sys.stderr, "Warning: File %s has multiple sources" % outfile
      return
    known_files.add(outfile)

    if os.path.exists(outfile):
      with codecs.open(outfile, "rb", encoding=encoding) as handle:
        if handle.read() == contents:
          return

    try:
      os.makedirs(os.path.dirname(outfile))
    except OSError, e:
      if e.errno != errno.EEXIST:
        raise

    with codecs.open(outfile, "wb", encoding=encoding) as handle:
      handle.write(contents)

  with MercurialSource(repo) as source:
    # Cache the result for some functions - we can assume here that the data
    # never changes
    source.resolve_link = cached(float("Infinity"))(source.resolve_link)
    source.read_config = cached(float("Infinity"))(source.read_config)
    source.read_template = cached(float("Infinity"))(source.read_template)
    source.read_locale = cached(float("Infinity"))(source.read_locale)
    source.read_include = cached(float("Infinity"))(source.read_include)

    locales = list(source.list_locales())
    for page, format in source.list_pages():
      for locale in locales:
        if source.has_locale(locale, page):
          pagedata = process_page(source, locale, page, format)

          # Make sure links to static files are versioned
          pagedata = re.sub(r'(<script\s[^<>]*\bsrc="/[^"<>]+)', r"\1?%s" % source.version, pagedata)
          pagedata = re.sub(r'(<link\s[^<>]*\bhref="/[^"<>]+)', r"\1?%s" % source.version, pagedata)
          pagedata = re.sub(r'(<img\s[^<>]*\bsrc="/[^"<>]+)', r"\1?%s" % source.version, pagedata)

          write_file([locale] + page.split("/"), pagedata)

    for filename in source.list_localizable_files():
      for locale in locales:
        if source.has_localizable_file(locale, filename):
          filedata = source.read_localizable_file(locale, filename)
          write_file([locale] + filename.split("/"), filedata, binary=True)

    for filename in source.list_static():
      write_file(filename.split("/"), source.read_static(filename), binary=True)

  def remove_unknown(dir):
    files = os.listdir(dir)
    for filename in files:
      path = os.path.join(dir, filename)
      if os.path.isfile(path) and path not in known_files:
        os.remove(path)
      elif os.path.isdir(path):
        remove_unknown(path)
        if not os.listdir(path):
          os.rmdir(path)
  remove_unknown(output_dir)

if __name__ == "__main__":
  setupStderr()
  if len(sys.argv) < 3:
    print >>sys.stderr, "Usage: %s source_repository output_dir" % sys.argv[0]
    sys.exit(1)

  repo, output_dir = sys.argv[1:3]
  generate_pages(repo, output_dir)
