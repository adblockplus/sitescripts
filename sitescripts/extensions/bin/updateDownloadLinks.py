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

"""
Update the list of extenstions
==============================

  This script generates a list of extensions and saves these with download links
  and version information
"""

import sys, os, re, urllib, urllib2, urlparse, subprocess, time
import xml.dom.minidom as dom
from ConfigParser import SafeConfigParser
from StringIO import StringIO
from sitescripts.utils import get_config, get_template
from sitescripts.extensions.utils import compareVersions, Configuration, getSafariCertificateID
from buildtools.packagerGecko import KNOWN_APPS

def urlencode(value):
  return urllib.quote(value.encode('utf-8'), '')

def urlopen(url, attempts=3):
  """
  Tries to open a particular URL, retries on failure.
  """
  for i in range(attempts):
    try:
      return urllib.urlopen(url)
    except IOError, e:
      error = e
      time.sleep(5)
  raise error

def getMozillaDownloadLink(galleryID):
  """
  gets download link for a Gecko add-on from the Mozilla Addons site
  """
  url = 'https://services.addons.mozilla.org/en-US/firefox/api/1/addon/%s' % urlencode(galleryID)
  contents = urlopen(url).read()
  document = dom.parseString(contents)
  linkTags = document.getElementsByTagName('install')
  linkTag = linkTags[0] if len(linkTags) > 0 else None
  versionTags = document.getElementsByTagName('version')
  versionTag = versionTags[0] if len(versionTags) > 0 else None
  if linkTag and versionTag and linkTag.firstChild and versionTag.firstChild:
    return (linkTag.firstChild.data, versionTag.firstChild.data)
  else:
    return (None, None)

def getGoogleDownloadLink(galleryID):
  """
  gets download link for a Chrome add-on from the Chrome Gallery site
  """
  param = 'id=%s&uc' % urlencode(galleryID)
  url = 'https://clients2.google.com/service/update2/crx?x=%s' % urlencode(param)
  contents = urlopen(url).read()
  document = dom.parseString(contents)
  updateTags = document.getElementsByTagName('updatecheck')
  updateTag = updateTags[0] if len(updateTags) > 0 else None
  if updateTag and updateTag.hasAttribute('codebase') and updateTag.hasAttribute('version'):
    return (updateTag.getAttribute('codebase'), updateTag.getAttribute('version'))
  else:
    return (None, None)

def getOperaDownloadLink(galleryID):
  """
  gets download link for an Opera add-on from the Opera Addons site
  """
  class HeadRequest(urllib2.Request):
    def get_method(self):
      return "HEAD"

  url = 'https://addons.opera.com/extensions/download/%s/' % urlencode(galleryID)
  response = urllib2.urlopen(HeadRequest(url))
  content_disposition = response.info().dict.get('content-disposition', None)
  if content_disposition != None:
    match = re.search(r'filename=\S+-([\d.]+)-\d+\.oex$', content_disposition)
  else:
    match = None;
  if match:
    return (url, match.group(1))
  else:
    return (None, None)

def getLocalLink(repo):
  """
  gets the link for the newest download of an add-on in the local downloads
  repository
  """
  url = repo.downloadsURL

  highestURL = None
  highestVersion = None

  if repo.type == 'android':
    prefix = os.path.basename(repo.repository)
  else:
    prefix = readRawMetadata(repo).get('general', 'basename')
  prefix += '-'
  suffix = repo.packageSuffix

  # go through the downloads repository looking for downloads matching this extension
  command = ['hg', 'locate', '-R', repo.downloadsRepo, '-r', 'default']
  result = subprocess.check_output(command)
  for fileName in result.splitlines():
    if fileName.startswith(prefix) and fileName.endswith(suffix):
      version = fileName[len(prefix):len(fileName) - len(suffix)]
      if highestVersion == None or compareVersions(version, highestVersion) > 0:
        highestURL = urlparse.urljoin(url, fileName)
        highestVersion = version
  return (highestURL, highestVersion)

def getDownloadLink(repo):
  """
  gets the download link to the most current version of an extension
  """
  galleryURL = None
  galleryVersion = None
  if repo.type == "gecko" and repo.galleryID:
    (galleryURL, galleryVersion) = getMozillaDownloadLink(repo.galleryID)
  elif repo.type == "chrome" and repo.galleryID:
    (galleryURL, galleryVersion) = getGoogleDownloadLink(repo.galleryID)
  elif repo.type == "opera" and repo.galleryID:
    (galleryURL, galleryVersion) = getOperaDownloadLink(repo.galleryID)

  (downloadsURL, downloadsVersion) = getLocalLink(repo)
  if galleryVersion == None or (downloadsVersion != None and
                                compareVersions(galleryVersion, downloadsVersion) < 0):
    return (downloadsURL, downloadsVersion)
  else:
    return (galleryURL, galleryVersion)

def getQRCode(text):
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
    (downloadURL, version) = getDownloadLink(repo)
    if downloadURL == None:
      continue
    if not result.has_section(repo.repositoryName):
      result.add_section(repo.repositoryName)
    result.set(repo.repositoryName, "downloadURL", downloadURL)
    result.set(repo.repositoryName, "version", version)

    qrcode = getQRCode(downloadURL)
    if qrcode != None:
      result.set(repo.repositoryName, "qrcode", qrcode)

def readRawMetadata(repo, version='tip'):
  files = subprocess.check_output(['hg', '-R', repo.repository, 'locate', '-r', version]).splitlines()
  genericFilename = 'metadata'
  filename = '%s.%s' % (genericFilename, repo.type)

  # Fall back to platform-independent metadata file
  if filename not in files:
    filename = genericFilename

  command = ['hg', '-R', repo.repository, 'cat', '-r', version, os.path.join(repo.repository, filename)]
  result = subprocess.check_output(command)

  parser = SafeConfigParser()
  parser.readfp(StringIO(result))

  return parser

def readMetadata(repo, version):
  """
  reads extension ID and compatibility information from metadata file in the
  extension's repository
  """
  if repo.type == 'android':
    command = ['hg', '-R', repo.repository, 'id', '-r', version, '-n']
    result = subprocess.check_output(command)
    revision = re.sub(r'\D', '', result)

    command = ['hg', '-R', repo.repository, 'cat', '-r', version, os.path.join(repo.repository, 'AndroidManifest.xml')]
    result = subprocess.check_output(command)
    manifest = dom.parseString(result)
    usesSdk = manifest.getElementsByTagName('uses-sdk')[0]

    return {
      'revision': revision,
      'minSdkVersion': usesSdk.attributes["android:minSdkVersion"].value,
    }
  elif repo.type == 'safari':
    metadata = readRawMetadata(repo, version)
    return {
      'certificateID': getSafariCertificateID(repo.keyFile),
      'version': version,
      'shortVersion': version,
      'basename': metadata.get('general', 'basename'),
    }
  elif repo.type == 'gecko':
    metadata = readRawMetadata(repo, version)
    result = {
      'extensionID': metadata.get('general', 'id'),
      'version': version,
      'compat': []
    }
    for key, value in KNOWN_APPS.iteritems():
      if metadata.has_option('compat', key):
        minVersion, maxVersion = metadata.get('compat', key).split('/')
        result['compat'].append({'id': value, 'minVersion': minVersion, 'maxVersion': maxVersion})
    return result
  else:
    raise Exception('unknown repository type %r' % repo.type)

def writeUpdateManifest(links):
  """
  writes an update manifest for all Gecko extensions and Android apps
  """

  extensions = {'gecko': [], 'android': [], 'safari': []}
  for repo in Configuration.getRepositoryConfigurations():
    if repo.type not in extensions or not links.has_section(repo.repositoryName):
      continue
    data = readMetadata(repo, links.get(repo.repositoryName, 'version'))
    data['updateURL'] = links.get(repo.repositoryName, 'downloadURL')
    if data['updateURL'].startswith(repo.downloadsURL):
      data['updateURL'] += "?update"
    extensions[repo.type].append(data)

  if len(extensions['android']) > 1:
    print >>sys.stderr, 'Warning: more than one Android app defined, update manifest only works for one'

  for repoType in extensions.iterkeys():
    manifestPath = get_config().get('extensions', '%sUpdateManifestPath' % repoType)
    template = get_template(get_config().get('extensions', '%sUpdateManifest' % repoType))
    template.stream({'extensions': extensions[repoType]}).dump(manifestPath)

def updateLinks():
  """
  writes the current extension download links to a file
  """

  # Now get download links and save them to file
  result = SafeConfigParser()
  getDownloadLinks(result)
  file = open(get_config().get('extensions', 'downloadLinksFile'), 'wb')
  result.write(file)
  file.close()

  writeUpdateManifest(result)

if __name__ == "__main__":
  updateLinks()
