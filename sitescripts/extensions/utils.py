# coding: utf-8

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

import re
from ConfigParser import NoOptionError
from sitescripts.utils import get_config

def compareVersionParts(part1, part2):
  def convertInt(value, default):
    try:
      return int(value)
    except ValueError:
      return default

  def convertVersionPart(part):
    if part == '*':
      # Special case - * is interpreted as Infinity
      return (1.0e300, '', 0, '')
    else:
      match = re.match(r'^(\d*)(\D*)(\d*)(.*)', part)
      a, b, c, d = (convertInt(match.group(1), 0), match.group(2), convertInt(match.group(3), 0), match.group(4))
      if b == '+':
        # Another special case - "2+" is the same as "3pre"
        a += 1
        b = 'pre'
      return (a, b, c, d)

  def compareStringPart(str1, str2):
    if str1 == str2:
      return 0

    # Missing strings are always larger
    if str1 == '':
      return 1
    if str2 == '':
      return -1

    if str1 < str2:
      return -1
    if str1 > str2:
      return 1
    raise Exception('This should never run, something is wrong')

  a1, b1, c1, d1 = convertVersionPart(part1)
  a2, b2, c2, d2 = convertVersionPart(part2)
  return (a1 - a2) or compareStringPart(b1, b2) or (c1 - c2) or compareStringPart(d1, d2)

def compareVersions(version1, version2):
  """
    Compares two version numbers according to the rules outlined on
    https://developer.mozilla.org/en/XPCOM_Interface_Reference/nsIVersionComparator.
    Returns a value smaller than 0 if first version number is smaller,
    larger than 0 if it is bigger, and 0 if the version numbers are effectively
    equal.
  """

  parts1 = version1.split('.')
  parts2 = version2.split('.')
  for i in range(0, max(len(parts1), len(parts2))):
    part1 = ''
    part2 = ''
    if i < len(parts1):
      part1 = parts1[i]
    if i < len(parts2):
      part2 = parts2[i]
    result = compareVersionParts(part1, part2)
    if result != None and result != 0:
      return result
  return 0

class Configuration(object):
  """
    This class represents the configuration settings for a single repository.
    Some of these properties come from the nightly config file and can be
    changed (latestRevision), others come from the global config and are
    read-only (repository, repositoryName, nightliesDirectory).
  """

  def _defineGlobalProperty(key):
    """
      Creates a property corresponding with a key in the config file
    """
    return property(lambda self: self.config.get('extensions', key))

  def _defineLocalProperty(key, default = None):
    """
      Creates a property corresponding with a repository-specific key in the config file
    """
    def getLocalProperty(self):
      try:
        return self.config.get('extensions', self.repositoryName + '_' + key)
      except NoOptionError, e:
        if default != None:
          return default
        else:
          raise e
    return property(getLocalProperty)

  def _defineNightlyProperty(key):
    """
      Creates a property corresponding with a key in the nightly config file
    """
    return property(lambda self: self.nightlyConfig.get(self.repositoryName, key),
                    lambda self, value: self.nightlyConfig.set(self.repositoryName, key, value))

  config = None
  nightlyConfig = None
  repositoryName = None
  repository = None

  buildRepository = _defineGlobalProperty('buildRepository')
  nightliesDirectory = _defineGlobalProperty('nightliesDirectory')
  nightliesURL = _defineGlobalProperty('nightliesURL')
  downloadsRepo = _defineGlobalProperty('downloadsRepo')
  downloadsURL = _defineGlobalProperty('downloadsURL')
  docsDirectory = _defineGlobalProperty('docsDirectory')
  signtool = _defineGlobalProperty('signtool')
  certname = _defineGlobalProperty('signtool_certname')
  dbdir = _defineGlobalProperty('signtool_dbdir')
  dbpass = _defineGlobalProperty('signtool_dbpass')

  keyFile = _defineLocalProperty('key', '')
  name = _defineLocalProperty('name')
  galleryID = _defineLocalProperty('galleryID', '')
  devbuildGalleryID = _defineLocalProperty('devbuildGalleryID', '')
  downloadPage = _defineLocalProperty('downloadPage', '')
  experimental = _defineLocalProperty('experimental', '')
  clientID = _defineLocalProperty('clientID', '')
  clientSecret = _defineLocalProperty('clientSecret', '')
  refreshToken = _defineLocalProperty('refreshToken', '')

  latestRevision = _defineNightlyProperty('latestRevision')

  def __init__(self, config, nightlyConfig, repositoryName, repository):
    """
      Creates a new Configuration instance that is bound to a particular
      repository.
    """

    self.repositoryName = repositoryName
    self.repository = repository
    self.config = config
    self.nightlyConfig = nightlyConfig

    if self.config.has_option('extensions', self.repositoryName + '_type'):
      self.type = self.config.get('extensions', self.repositoryName + '_type')
    else:
      self.type = 'gecko'

    if self.type == 'gecko':
      self.packageSuffix = '.xpi'
    elif self.type == 'chrome' or self.type == 'opera':
      self.packageSuffix = '.crx'
    elif self.type == 'safari':
      self.packageSuffix = '.safariextz'
    elif self.type == 'ie':
      self.packageSuffix = '-x64.msi'
    elif self.type == 'android':
      self.packageSuffix = '.apk'

    if self.nightlyConfig and not self.nightlyConfig.has_section(self.repositoryName):
      self.nightlyConfig.add_section(self.repositoryName)

  def __str__(self):
    """
      Provides a string representation of this configuration
    """
    return self.repositoryName

  @staticmethod
  def getRepositoryConfigurations(nightlyConfig = None):
    """
      Retrieves configuration settings for all repositories
      from the configuration file, where existing repositories
      are identified by an <id>_repository entry appearing
      in the configuration file.
      This static method will enumerate Configuration
      objects representing the settings for each repository.
    """
    config = get_config()
    for key, value in config.items("extensions"):
      if key.endswith("_repository"):
        repositoryName = re.sub(r'_repository$', '', key)
        if repositoryName:
          yield Configuration(config, nightlyConfig, repositoryName, value)

def getSafariCertificateID(keyFile):
  import M2Crypto

  bio = M2Crypto.BIO.openfile(keyFile)
  try:
    while True:
      try:
        cert = M2Crypto.X509.load_cert_bio(bio)
      except M2Crypto.X509.X509Error:
        raise Exception('No safari developer certificate found in chain')

      subject = cert.get_subject()
      for entry in subject.get_entries_by_nid(subject.nid['CN']):
        m = re.match(r'Safari Developer: \((.*?)\)', entry.get_data().as_text())
        if m:
          return m.group(1)
  finally:
    bio.close()
