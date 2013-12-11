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

import os, imp, re, jinja2, markdown
from ..utils import get_custom_template_environment

# Monkey-patch Markdown's isBlockLevel function to ensure that no paragraphs are
# inserted into the <head> tag
orig_isBlockLevel = markdown.util.isBlockLevel
def isBlockLevel(tag):
  if tag == "head":
    return True
  else:
    return orig_isBlockLevel(tag)
markdown.util.isBlockLevel = isBlockLevel

html_escapes = {
  "<": "&lt;",
  ">": "&gt;",
  "&": "&amp;",
  "\"": "&quot;",
  "'": "&#39;",
}

class Converter:
  def __init__(self, params, key="pagedata"):
    self._params = params
    self._key = key

    # Read in any parameters specified at the beginning of the file
    lines = params[key].splitlines(True)
    while lines and re.search(r"^\s*[\w\-]+\s*=", lines[0]):
      name, value = lines.pop(0).split("=", 1)
      params[name.strip()] = value.strip()
    params[key] = "".join(lines)

  def localize_string(self, name, localedata, escapes, links=[]):
    def escape(s):
      return re.sub(r".",
        lambda match: escapes.get(match.group(0), match.group(0)),
        s, flags=re.S)
    def re_escape(s):
      return re.escape(escape(s))

    try:
      result = localedata[name].strip()
    except KeyError:
      raise Exception("Lookup failed for string %s used on page %s" % (name, self._params["page"]))

    # Insert links
    result = escape(result)
    while links:
      result = re.sub(
        r"%s([^<>]*?)%s" % (re_escape("<a>"), re_escape("</a>")),
        r'<a href="%s">\1</a>' % links.pop(0),
        result, 1, flags=re.S
      )

    # <strong> and <em> tags are allowed
    result = re.sub(
      r"%s([^<>]*?)%s" % (re_escape("<strong>"), re_escape("</strong>")),
      r"<strong>\1</strong>",
      result, flags=re.S
    )
    result = re.sub(
      r"%s([^<>]*?)%s" % (re_escape("<em>"), re_escape("</em>")),
      r"<em>\1</em>",
      result, flags=re.S
    )
    return result

  def insert_localized_strings(self, text, escapes):
    def lookup_string(match):
      name, links = match.groups()
      if links:
        links = map(unicode.strip, links.strip("()").split(","))
      else:
        links = []
      return self.localize_string(name, self._params["localedata"], escapes, links)

    return re.sub(
      r"\$([\w\-]+)(\([^()$]+\))?\$",
      lookup_string,
      text
    )

  def process_links(self, text):
    def process_link(match):
      pre, attr, url, post = match.groups()
      url = jinja2.Markup(url).unescape()

      locale, new_url = self._params["source"].resolve_link(url, self._params["locale"])
      if new_url != None:
        url = new_url
        if attr == "href":
          post += ' hreflang="%s"' % jinja2.Markup.escape(locale)

      return "".join((pre, jinja2.Markup.escape(url), post))

    text = re.sub(r"(<a\s[^<>]*\b(href)=\")([^<>\"]+)(\")", process_link, text)
    text = re.sub(r"(<img\s[^<>]*\b(src)=\")([^<>\"]+)(\")", process_link, text)
    return text

  def resolve_includes(self, text):
    def resolve_include(match):
      global converters
      name = match.group(1)
      for format, converter_class in converters.iteritems():
        if self._params["source"].has_include(name, format):
          self._params["includedata"] = self._params["source"].read_include(name, format)
          converter = converter_class(self._params, key="includedata")
          return converter()
      raise Exception("Failed to resolve include %s in page %s" % (name, self._params["page"]))

    return re.sub(r'<\?\s*include\s+([^\s<>"]+)\s*\?>', resolve_include, text)

  def __call__(self):
    result = self.get_html(self._params[self._key])
    result = self.resolve_includes(result)
    if self._key == "pagedata":
      head = []
      def add_to_head(match):
        head.append(match.group(1))
        return ""
      body = re.sub(r"<head>(.*?)</head>", add_to_head, result, flags=re.S)
      return "".join(head), body
    else:
      return result

class RawConverter(Converter):
  def get_html(self, source):
    result = self.insert_localized_strings(source, html_escapes)
    result = self.process_links(result)
    return result

class MarkdownConverter(Converter):
  def get_html(self, source):
    def remove_unnecessary_entities(match):
      char = unichr(int(match.group(1)))
      if char in html_escapes:
        return match.group(0)
      else:
        return char

    escapes = {}
    for char in markdown.Markdown.ESCAPED_CHARS:
      escapes[char] = "&#" + str(ord(char)) + ";"
    for key, value in html_escapes.iteritems():
      escapes[key] = value

    md = markdown.Markdown(output="html5", extensions=["attr_list"])
    md.preprocessors["html_block"].markdown_in_raw = True

    result = self.insert_localized_strings(source, escapes)
    result = md.convert(result)
    result = re.sub(r"&#(\d+);", remove_unnecessary_entities, result)
    result = self.process_links(result)
    return result

class TemplateConverter(Converter):
  def __init__(self, *args, **kwargs):
    Converter.__init__(self, *args, **kwargs)

    filters = {
      "translate": self.translate,
      "linkify": self.linkify,
      "toclist": self.toclist,
    }

    for filename in self._params["source"].list_files("filters"):
      root, ext = os.path.splitext(filename)
      if ext.lower() != ".py":
        continue

      path = "%s/%s" % ("filters", filename)
      code = self._params["source"].read_file(path)
      module = imp.new_module(root.replace("/", "."))
      exec code in module.__dict__

      func = os.path.basename(root)
      if not hasattr(module, func):
        raise Exception("Expected function %s not found in filter file %s" % (func, filename))
      filters[func] = getattr(module, func)
      filters[func].module_ref = module  # Prevent garbage collection

    self._env = get_custom_template_environment(filters)

  def get_html(self, source):
    template = self._env.from_string(source)
    return template.render(self._params)

  def translate(self, name, page=None, links=[]):
    if page == None:
      localedata = self._params["localedata"]
    else:
      localedata = self._params["source"].read_locale(self._params["locale"], page)
    return jinja2.Markup(self.localize_string(name, localedata, html_escapes, links=links))

  def linkify(self, page, locale=None):
    if locale == None:
      locale = self._params["locale"]

    locale, url = self._params["source"].resolve_link(page, locale)
    return jinja2.Markup('<a href="%s" hreflang="%s">' % (
      jinja2.Markup.escape(url),
      jinja2.Markup.escape(locale)
    ))

  def toclist(self, content):
    flat = []
    for match in re.finditer(r'<h(\d)\s[^<>]*\bid="([^<>"]+)"[^<>]*>(.*?)</h\1>', content, re.S):
      flat.append({
        "level": int(match.group(1)),
        "anchor": jinja2.Markup(match.group(2)).unescape(),
        "title": jinja2.Markup(match.group(3)).unescape(),
        "subitems": [],
      })

    structured = []
    stack = [{"level": 0, "subitems": structured}]
    for item in flat:
      while stack[-1]["level"] >= item["level"]:
        stack.pop()
      stack[-1]["subitems"].append(item)
      stack.append(item)
    return structured

converters = {
  "raw": RawConverter,
  "md": MarkdownConverter,
  "tmpl": TemplateConverter,
}
