# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2014 Eyeo GmbH
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

import subprocess
import os
import re
import time
from datetime import datetime
from urlparse import urljoin

from sitescripts.utils import get_template
from sitescripts.extensions.android import get_min_android_version
from sitescripts.extensions.pad.language import iso2pad
from sitescripts.extensions.pad.validation import validate_pad

OS_WINDOWS = ['Windows 8', 'Win7 x32', 'Win7 x64', 'WinVista', 'WinVista x64', 'WinXP']
OS_LINUX = ['Linux']
OS_MAC = ['Mac OS X']
OS_ANDROID = ['Android']

class PadFile:
  def __init__(self, repo, version, download_url):
    self.repo = repo
    self.version = version
    self.download_url = download_url

    self.first_release = True
    for i, (filename, version) in enumerate(repo.getDownloads()):
      if i > 0:
        self.first_release = False

      if version == self.version:
        self.download_filename = filename

  @property
  def release_status(self):
    if self.first_release:
      return 'New Release'

    if self.version.rstrip('.0').count('.') < 2:
      return 'Major Update'

    return 'Minor Update'

  @property
  def release_date(self):
    command = ['hg', 'log', '-l', '1', self.download_filename, '--template', '{date}']
    result = subprocess.check_output(command, cwd=self.repo.downloadsRepo)
    timestamp, offset = re.match(r'(.*)([-+].*)', result).groups()
    return datetime(*time.gmtime(float(timestamp) + float(offset))[:6])

  @property
  def download_size(self):
    return len(subprocess.check_output(
      ['hg', 'cat', '-r', 'tip', self.download_filename],
      cwd=self.repo.downloadsRepo
    ))

  @property
  def browser_min_version(self):
    metadata = self.repo.readMetadata(self.version)
    compat_option = getattr(self, 'compat_option',  self.repo.type)
    return metadata.get('compat', compat_option).split('/')[0].rstrip('.0')

  @property
  def languages(self):
    files = self.repo.listContents(self.version)
    languages = set()
    skipped = set()

    for filename in files:
      match = re.match(self.translation_files_regex, filename)

      if match:
        groups = match.groupdict()

        # support translation files that vary from the naming
        # scheme like the default translation for Android
        for k, v in groups.iteritems():
          if k.startswith('is_') and v is not None:
            code = k[3:]
            break
        else:
          code = groups['code']

        # support .incomplete files like on Firefox
        if groups.get('skip') is not None:
          skipped.add(code)
          continue

        languages.add(code)

    return iso2pad(languages.difference(skipped))

  def write(self):
    template = get_template(self.repo.padTemplate)
    basename = self.repo.basename
    filename = basename + '.xml'

    pad = template.render({
      'name': self.repo.name,
      'type': self.repo.type,
      'basename': basename,
      'browser_name': self.browser_name,
      'browser_min_version': self.browser_min_version,
      'version': self.version,
      'release_date': self.release_date,
      'release_status': self.release_status,
      'os_support': ','.join(self.os_support),
      'language': ','.join(self.languages),
      'download_size': self.download_size,
      'download_url': self.download_url,
      'pad_url': urljoin(self.repo.padURL, filename),
    }).encode('utf-8')

    path = os.path.join(self.repo.padDirectory, filename)
    validate_pad(pad, path)

    with open(path, 'wb') as file:
      file.write(pad)

  @staticmethod
  def forRepository(repo, *args, **kwargs):
    if repo.type == 'gecko':
      return FirefoxPadFile(repo, *args, **kwargs)
    if repo.type == 'chrome':
      return ChromePadFile(repo, *args, **kwargs)
    if repo.type == 'opera':
      return OperaPadFile(repo, *args, **kwargs)
    if repo.type == 'safari':
      return SafariPadFile(repo, *args, **kwargs)
    if repo.type == 'ie':
      return InternetExplorerPadFile(repo, *args, **kwargs)
    if repo.type == 'android':
      return AndroidPadFile(repo, *args, **kwargs)

    raise Exception('unknown repository type %r' % repo.type)

class FirefoxPadFile(PadFile):
  browser_name = 'Mozilla Firefox'
  os_support = OS_WINDOWS + OS_MAC + OS_LINUX + OS_ANDROID
  translation_files_regex = r'chrome\/locale\/(?P<code>.+?)\/(?P<skip>\.incomplete$)?'
  compat_option = 'firefox'

class ChromePadFile(PadFile):
  browser_name = 'Google Chrome'
  os_support = OS_WINDOWS + OS_MAC + OS_LINUX
  translation_files_regex = r'_locales\/(?P<code>.+?)\/'

class OperaPadFile(PadFile):
  browser_name = 'Opera'
  browser_min_version = '17'
  os_support = OS_WINDOWS + OS_MAC + OS_LINUX
  translation_files_regex = ChromePadFile.translation_files_regex

class SafariPadFile(PadFile):
  browser_name = 'Safari'
  browser_min_version = '6'
  os_support = OS_MAC
  translation_files_regex = ChromePadFile.translation_files_regex

class InternetExplorerPadFile(PadFile):
  browser_name = 'Internet Explorer'
  browser_min_version = '8'
  os_support = OS_WINDOWS
  translation_files_regex = r'locales\/(?P<code>.+)\.ini$'

class AndroidPadFile(PadFile):
  browser_name = 'Android'
  os_support = OS_ANDROID
  translation_files_regex = r'res\/(?:raw|values)(?:-(?P<code>.+?)|(?P<is_en>))\/'

  @property
  def browser_min_version(self):
    return get_min_android_version(self.repo, self.version)
