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

import sys, os, flask
from ...utils import setupStderr
from ..utils import process_page
from ..sources import FileSource
from ..converters import converters

app = flask.Flask("sitescripts.cms.bin.test_server")
source = None

mime_types = {
  "": "text/html; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".xml": "text/xml; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
}

def get_data(path):
  if source.has_static(path):
    return source.read_static(path)

  path = path.rstrip("/")
  if path == "":
    path = source.read_config().get("general", "defaultlocale")
  if "/" not in path:
    path = "%s/%s" % (path, source.read_config().get("general", "defaultpage"))

  locale, page = path.split("/", 1)
  for format in converters.iterkeys():
    if source.has_page(page, format):
      return process_page(source, locale, page, format).encode("utf-8")
  if source.has_localizable_file(locale, page):
    return source.read_localizable_file(locale, page)

  return None

@app.route("/", methods = ["GET"])
@app.route("/<path:path>", methods = ["GET"])
def show(path=""):
  data = get_data(path)
  if data == None:
    flask.abort(404)

  root, ext = os.path.splitext(path)
  mime = mime_types.get(ext.lower(), "application/octet-stream")
  return data, 200, {"Content-Type": mime}

if __name__ == "__main__":
  setupStderr()
  if len(sys.argv) < 2:
    print >>sys.stderr, "Usage: %s source_dir" % sys.argv[0]
    sys.exit(1)

  source = FileSource(sys.argv[1])

  # Make sure to "fix" argv to ensure that restart can succeed
  sys.argv[0:1] = ["-m", "sitescripts.cms.bin.test_server"]

  app.run(debug=True)
