# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-present eyeo GmbH
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

import codecs
import contextlib
import os
import json
import re
import subprocess
import traceback
import time
import urlparse
import urllib
import xml.dom.minidom as dom
from ConfigParser import SafeConfigParser, NoOptionError
from StringIO import StringIO
from sitescripts.utils import get_config
from xml.parsers.expat import ExpatError

PACKAGE_SUFFIXES = {
    'gecko': '.xpi',
    'chrome': '.crx',
    'safari': '.safariextz',
    'ie': '.exe',
    'android': '.apk',
    'edge': '.appx'
}


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
    def _defineProperty(name, local=False, type='', default=None):
        def getter(self):
            method = getattr(self.config, 'get' + type)
            key = '%s_%s' % (self.repositoryName, name) if local else name

            try:
                return method('extensions', key)
            except NoOptionError:
                if default is None:
                    raise
                return default

        return property(getter)

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

    spiderMonkeyBinary = _defineProperty('spiderMonkeyBinary', default='')
    nightliesDirectory = _defineProperty('nightliesDirectory')
    nightliesURL = _defineProperty('nightliesURL')
    downloadsRepo = _defineProperty('downloadsRepo')
    downloadsURL = _defineProperty('downloadsURL')
    docsDirectory = _defineProperty('docsDirectory')
    signtool = _defineProperty('signtool')
    certname = _defineProperty('signtool_certname')
    dbdir = _defineProperty('signtool_dbdir')
    dbpass = _defineProperty('signtool_dbpass')

    keyFile = _defineProperty('key', local=True, default='')
    name = _defineProperty('name', local=True)
    galleryID = _defineProperty('galleryID', local=True, default='')
    devbuildGalleryID = _defineProperty('devbuildGalleryID', local=True, default='')
    downloadPage = _defineProperty('downloadPage', local=True, default='')
    clientID = _defineProperty('clientID', local=True, default='')
    clientSecret = _defineProperty('clientSecret', local=True, default='')
    refreshToken = _defineProperty('refreshToken', local=True, default='')
    tenantID = _defineProperty('tenantID', local=True, default='')
    revision = _defineProperty('revision', local=True, default='master')

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
        self.packageSuffix = PACKAGE_SUFFIXES[self.type]

        if self.nightlyConfig and not self.nightlyConfig.has_section(self.repositoryName):
            self.nightlyConfig.add_section(self.repositoryName)

    def __str__(self):
        """
          Provides a string representation of this configuration
        """
        return self.repositoryName

    def readMetadata(self, version):
        genericFilename = 'metadata'
        filename = '%s.%s' % (genericFilename, self.type)
        files = subprocess.check_output(['hg', '-R', self.repository,
                                         'locate', '-r', version]).splitlines()

        if filename not in files:
            # some repositories like those for Android and
            # Internet Explorer don't have metadata files
            if genericFilename not in files:
                return None

            # Fall back to platform-independent metadata file
            filename = genericFilename

        command = ['hg', '-R', self.repository, 'cat', '-r', version, os.path.join(self.repository, filename)]
        result = subprocess.check_output(command)

        parser = SafeConfigParser()
        parser.readfp(StringIO(result))

        return parser

    def getDownloads(self):
        metadata = self.readMetadata(self.revision)
        if metadata:
            prefix = metadata.get('general', 'basename')
        else:
            prefix = os.path.basename(os.path.normpath(self.repository))
        prefix += '-'

        command = ['hg', 'locate', '-R', self.downloadsRepo, '-r', 'default']
        for filename in subprocess.check_output(command).splitlines():
            if filename.startswith(prefix) and filename.endswith(self.packageSuffix):
                yield (filename, filename[len(prefix):len(filename) - len(self.packageSuffix)])

    @staticmethod
    def getRepositoryConfigurations(nightlyConfig=None):
        """
          Retrieves configuration settings for all repositories
          from the configuration file, where existing repositories
          are identified by an <id>_repository entry appearing
          in the configuration file.
          This static method will enumerate Configuration
          objects representing the settings for each repository.
        """
        config = get_config()
        for key, value in config.items('extensions'):
            if key.endswith('_repository'):
                repositoryName = re.sub(r'_repository$', '', key)
                if repositoryName:
                    yield Configuration(config, nightlyConfig, repositoryName, value)


def _urlencode(value):
    return urllib.quote(value.encode('utf-8'), '')


def _urlopen(url, attempts=3):
    """
    Tries to open a particular URL, retries on failure.
    """
    for i in range(attempts):
        try:
            return contextlib.closing(urllib.urlopen(url))
        except IOError as e:
            error = Exception('Error {0} while opening {1} url'
                              .format(e, url))
            time.sleep(5)
    raise error


def _parseXMLDocument(url, attempts=2):
    for i in range(attempts):
        with _urlopen(url) as page:
            content = page.read()
        try:
            return dom.parseString(content)
        except ExpatError as err:
            exception = Exception('Error {0} while parsing xml:\n{1}\nfrom {2}'
                                  .format(err, content, url))
    raise exception


def _getMozillaDownloadLink(galleryID):
    """
    gets download link for a Gecko add-on from the Mozilla Addons site
    """
    url = 'https://services.addons.mozilla.org/en-US/firefox/api/1/addon/%s' % _urlencode(galleryID)
    document = _parseXMLDocument(url)
    linkTags = document.getElementsByTagName('install')
    linkTag = linkTags[0] if len(linkTags) > 0 else None
    versionTags = document.getElementsByTagName('version')
    versionTag = versionTags[0] if len(versionTags) > 0 else None
    if linkTag and versionTag and linkTag.firstChild and versionTag.firstChild:
        return (linkTag.firstChild.data, versionTag.firstChild.data)
    else:
        return (None, None)


def _getLocalLink(repo):
    """
    gets the link for the newest download of an add-on in the local downloads
    repository
    """
    highestURL = None
    highestVersion = None

    for filename, version in repo.getDownloads():
        if not highestVersion or compareVersions(version, highestVersion) > 0:
            highestURL = urlparse.urljoin(repo.downloadsURL, filename)
            highestVersion = version

    return (highestURL, highestVersion)


def _getDownloadLink(repo):
    """
    gets the download link to the most current version of an extension
    """
    if repo.galleryID and repo.type == 'gecko':
        return _getMozillaDownloadLink(repo.galleryID)
    return _getLocalLink(repo)


def _getQRCode(text):
    try:
        import qrcode
        import base64
        import Image    # required by qrcode but not formally a dependency
    except:
        return None

    data = StringIO()
    qrcode.make(text, box_size=5).save(data, 'png')
    return 'data:image/png;base64,' + base64.b64encode(data.getvalue())


def getDownloadLinks(result):
    """
    gets the download links for all extensions and puts them into the config
    object
    """
    for repo in Configuration.getRepositoryConfigurations():
        try:
            (downloadURL, version) = _getDownloadLink(repo)
            if downloadURL is None:
                raise Exception('No download link found for repo: ' +
                                repo.repositoryName)
        except:
            traceback.print_exc()
            continue
        if not result.has_section(repo.repositoryName):
            result.add_section(repo.repositoryName)
        result.set(repo.repositoryName, 'downloadURL', downloadURL)
        result.set(repo.repositoryName, 'version', version)

        qrcode = _getQRCode(downloadURL)
        if qrcode is not None:
            result.set(repo.repositoryName, 'qrcode', qrcode)


def writeLibabpUpdateManifest(path, updates):
    """
      Writes update.json file for libadblockplus
    """

    baseDir = os.path.dirname(path)
    if not os.path.exists(baseDir):
        os.makedirs(baseDir)

    handle = codecs.open(path, 'wb', encoding='UTF-8')
    json.dump(updates, handle, ensure_ascii=False, indent=2, separators=(',', ': '))
    handle.close()


def writeIEUpdateManifest(path, extensions):
    """
      Writes update.json for IE
    """

    if not extensions:
        return

    updates = {}
    for extension in extensions:
        basename = extension['basename']
        updateURL = extension['updateURL']
        version = extension['version']
        updates['%s/%s' % (basename, 'msie64')] = {
            'url': updateURL.replace('.exe', '-x64.msi'),
            'version': version
        }
        updates['%s/%s' % (basename, 'msie32')] = {
            'url': updateURL.replace('.exe', '-x86.msi'),
            'version': version
        }
    writeLibabpUpdateManifest(path, updates)


def writeAndroidUpdateManifest(path, extensions):
    """
      Writes update.json for Android
    """

    if not extensions:
        return

    updates = {}
    for extension in extensions:
        updates[extension['basename']] = {
            'url': extension['updateURL'],
            'version': extension['version']
        }
    writeLibabpUpdateManifest(path, updates)
