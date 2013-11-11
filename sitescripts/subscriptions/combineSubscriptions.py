#!/usr/bin/env python
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

import sys, os, re, subprocess, urllib2, time, traceback, codecs, hashlib, base64, tempfile
from getopt import getopt, GetoptError

accepted_extensions = set([".txt"])
ignore = set(["Apache.txt", "CC-BY-SA.txt", "GPL.txt", "MPL.txt"])
verbatim = set(["COPYING"])

def combine_subscriptions(sources, target_dir, timeout=30, tempdir=None):
  if not os.path.exists(target_dir):
    os.makedirs(target_dir, 0755)

  def save_file(filename, data):
    handle = tempfile.NamedTemporaryFile(mode="wb", dir=tempdir, delete=False)
    handle.write(data.encode("utf-8"))
    handle.close()

    try:
      subprocess.check_output(["7za", "a", "-tgzip", "-mx=9", "-bd", "-mpass=5", handle.name + ".gz", handle.name])
    except:
      print >>sys.stderr, "Failed to compress file %s. Please ensure that p7zip is installed on the system." % handle.name

    path = os.path.join(target_dir, filename)
    os.rename(handle.name, path)
    os.rename(handle.name + ".gz", path + ".gz")

  known = set()
  for source_name, source in sources.iteritems():
    for filename in source.list_top_level_files():
      if filename in ignore or filename.startswith("."):
        continue
      if filename in verbatim:
        process_verbatim_file(source, save_file, filename)
      elif not os.path.splitext(filename)[1] in accepted_extensions:
        continue
      else:
        try:
          process_subscription_file(source_name, sources, save_file, filename, timeout)
        except:
          print >>sys.stderr, 'Error processing subscription file "%s"' % filename
          traceback.print_exc()
          print >>sys.stderr
        known.add(os.path.splitext(filename)[0] + ".tpl")
        known.add(os.path.splitext(filename)[0] + ".tpl.gz")
      known.add(filename)
      known.add(filename + ".gz")

  for filename in os.listdir(target_dir):
    if filename.startswith("."):
      continue
    if not filename in known:
      os.remove(os.path.join(target_dir, filename))

def process_verbatim_file(source, save_file, filename):
  save_file(filename, source.read_file(filename))

def process_subscription_file(source_name, sources, save_file, filename, timeout):
  source = sources[source_name]
  lines = source.read_file(filename).splitlines()

  header = ""
  if len(lines) > 0:
    header = lines.pop(0)
  if not re.search(r"\[Adblock(?:\s*Plus\s*([\d\.]+)?)?\]", header, re.I):
    raise Exception("This is not a valid Adblock Plus subscription file.")

  lines = resolve_includes(source_name, sources, lines, timeout)
  seen = set(["checksum", "version"])
  def check_line(line):
    if line == "":
      return False
    match = re.search(r"^\s*!\s*(Redirect|Homepage|Title|Checksum|Version)\s*:", line, re.M | re.I)
    if not match:
      return True
    key = match.group(1).lower()
    if key in seen:
      return False
    seen.add(key)
    return True
  lines = filter(check_line, lines)

  write_tpl(save_file, os.path.splitext(filename)[0] + ".tpl", lines)

  lines.insert(0, "! Version: %s" % time.strftime("%Y%m%d%H%M", time.gmtime()))

  checksum = hashlib.md5()
  checksum.update("\n".join([header] + lines).encode("utf-8"))
  lines.insert(0, "! Checksum: %s" % base64.b64encode(checksum.digest()).rstrip("="))
  lines.insert(0, header)
  save_file(filename, "\n".join(lines))

def resolve_includes(source_name, sources, lines, timeout, level=0):
  if level > 5:
    raise Exception("There are too many nested includes, which is probably the result of a circular reference somewhere.")

  result = []
  for line in lines:
    match = re.search(r"^\s*%include\s+(.*)%\s*$", line)
    if match:
      filename = match.group(1)
      newlines = None
      if re.match(r"^https?://", filename):
        result.append("! *** Fetched from: %s ***" % filename)

        for i in range(3):
          try:
            request = urllib2.urlopen(filename, None, timeout)
            data = request.read()
            error = None
            break
          except urllib2.URLError, e:
            error = e
            time.sleep(5)
        if error:
          raise error

        # We should really get the charset from the headers rather than assuming
        # that it is UTF-8. However, some of the Google Code mirrors are
        # misconfigured and will return ISO-8859-1 as charset instead of UTF-8.
        newlines = data.decode("utf-8").splitlines()
        newlines = filter(lambda l: not re.search(r"^\s*!.*?\bExpires\s*(?::|after)\s*(\d+)\s*(h)?", l, re.M | re.I), newlines)
        newlines = filter(lambda l: not re.search(r"^\s*!\s*(Redirect|Homepage|Title|Version)\s*:", l, re.M | re.I), newlines)
      else:
        result.append("! *** %s ***" % filename)

        include_source = source_name
        if ":" in filename:
          include_source, filename = filename.split(":", 1)
        if not include_source in sources:
          raise Exception('Cannot include file from repository "%s", this repository is unknown' % include_source)

        source = sources[include_source]
        newlines = source.read_file(filename).splitlines()
        newlines = resolve_includes(include_source, sources, newlines, timeout, level + 1)

      if len(newlines) and re.search(r"\[Adblock(?:\s*Plus\s*([\d\.]+)?)?\]", newlines[0], re.I):
        del newlines[0]
      result.extend(newlines)
    else:
      if line.find("%timestamp%") >= 0:
        if level == 0:
          line = line.replace("%timestamp%", time.strftime("%d %b %Y %H:%M UTC", time.gmtime()))
        else:
          line = ""
      result.append(line)
  return result

def write_tpl(save_file, filename, lines):
  result = []
  result.append("msFilterList")
  for line in lines:
    if re.search(r"^\s*!", line):
      # This is a comment. Handle "Expires" comment in a special way, keep the rest.
      match = re.search(r"\bExpires\s*(?::|after)\s*(\d+)\s*(h)?", line, re.I)
      if match:
        interval = int(match.group(1))
        if match.group(2):
          interval = int(interval / 24)
        result.append(": Expires=%i" % interval)
      else:
        result.append(re.sub(r"^\s*!", "#", re.sub(r"--!$", "--#", line)))
    elif line.find("#") >= 0:
      # Element hiding rules are not supported in MSIE, drop them
      pass
    else:
      # We have a blocking or exception rule, try to convert it
      origline = line

      is_exception = False
      if line.startswith("@@"):
        is_exception = True
        line = line[2:]

      has_unsupported = False
      requires_script = False
      match = re.search(r"^(.*?)\$(.*)", line)
      if match:
        # This rule has options, check whether any of them are important
        line = match.group(1)
        options = match.group(2).replace("_", "-").lower().split(",")

        # Remove first-party only exceptions, we will allow an ad server everywhere otherwise
        if is_exception and "~third-party" in options:
          has_unsupported = True

        # A number of options are not supported in MSIE but can be safely ignored, remove them
        options = filter(lambda o: not o in ("", "third-party", "~third-party", "match-case", "~match-case", "~other", "~donottrack"), options)

        # Also ignore domain negation of whitelists
        if is_exception:
          options = filter(lambda o: not o.startswith("domain=~"), options)

        unsupported = filter(lambda o: o in ("other", "elemhide"), options)
        if unsupported and len(unsupported) == len(options):
          # The rule only applies to types that are not supported in MSIE
          has_unsupported = True
        elif "donottrack" in options:
          # Do-Not-Track rules have to be removed even if $donottrack is combined with other options
          has_unsupported = True
        elif "script" in options and len(options) == len(unsupported) + 1:
          # Mark rules that only apply to scripts for approximate conversion
          requires_script = True
        elif len(options) > 0:
          # The rule has further options that aren't available in TPLs. For
          # exception rules that aren't specific to a domain we ignore all
          # remaining options to avoid potential false positives. Other rules
          # simply aren't included in the TPL file.
          if is_exception:
            has_unsupported = any([o.startswith("domain=") for o in options])
          else:
            has_unsupported = True

      if has_unsupported:
        # Do not include filters with unsupported options
        result.append("# " + origline)
      else:
        line = line.replace("^", "/") # Assume that separator placeholders mean slashes

        # Try to extract domain info
        domain = None
        match = re.search(r"^(\|\||\|\w+://)([^*:/]+)(:\d+)?(/.*)", line)
        if match:
          domain = match.group(2)
          line = match.group(4)
        else:
          # No domain info, remove anchors at the rule start
          line = re.sub(r"^\|\|", "http://", line)
          line = re.sub(r"^\|", "", line)
        # Remove anchors at the rule end
        line = re.sub(r"\|$", "", line)
        # Remove unnecessary asterisks at the ends of lines
        line = re.sub(r"\*$", "", line)
        # Emulate $script by appending *.js to the rule
        if requires_script:
          line += "*.js"
        if line.startswith("/*"):
          line = line[2:]
        if domain:
          line = "%sd %s %s" % ("+" if is_exception else "-", domain, line)
          line = re.sub(r"\s+/$", "", line)
          result.append(line)
        elif is_exception:
          # Exception rules without domains are unsupported
          result.append("# " + origline)
        else:
          result.append("- " + line)
  save_file(filename, "\n".join(result) + "\n")

class FileSource:
  def __init__(self, dir):
    self._dir = dir
    if os.path.exists(os.path.join(dir, ".hg")):
      # This is a Mercurial repository, try updating
      subprocess.call(["hg", "-q", "-R", dir, "pull", "--update"])

  def get_path(self, filename):
    return os.path.join(self._dir, *filename.split("/"))

  def read_file(self, filename):
    path = self.get_path(filename)
    if os.path.relpath(path, self._dir).startswith("."):
      raise Exception("Attempt to access a file outside the repository")
    with codecs.open(path, "rb", encoding="utf-8") as handle:
      return handle.read()

  def list_top_level_files(self):
    for filename in os.listdir(self._dir):
      path = os.path.join(self._dir, filename)
      if os.path.isfile(path):
        yield filename

def usage():
  print """Usage: %s source_name=source_dir ... [output_dir]

Options:
  -h          --help              Print this message and exit
  -t seconds  --timeout=seconds   Timeout when fetching remote subscriptions
""" % os.path.basename(sys.argv[0])

if __name__ == "__main__":
  try:
    opts, args = getopt(sys.argv[1:], "ht:", ["help", "timeout="])
  except GetoptError, e:
    print str(e)
    usage()
    sys.exit(2)

  target_dir = "subscriptions"
  sources = {}
  for arg in args:
    if "=" in arg:
      source_name, source_dir = arg.split("=", 1)
      sources[source_name] = FileSource(source_dir)
    else:
      target_dir = arg
  if not sources:
    sources[""] = FileSource(".")

  timeout = 30
  for option, value in opts:
    if option in ("-h", "--help"):
      usage()
      sys.exit()
    elif option in ("-t", "--timeout"):
      timeout = int(value)

  combine_subscriptions(sources, target_dir, timeout)
