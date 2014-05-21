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
from sitescripts.extensions.android import get_min_sdk_version
from sitescripts.extensions.pad import PadFile
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
  galleryID = urlencode(galleryID)

  url = 'https://clients2.google.com/service/update2/crx?x=%s' % urlencode('id=%s&uc' % galleryID)
  document = dom.parse(urlopen(url))
  updateTags = document.getElementsByTagName('updatecheck')
  version = updateTags and updateTags[0].getAttribute('version')

  if not version:
    return (None, None)

  request = urllib2.Request('https://chrome.google.com/webstore/detail/_/' + galleryID)
  request.get_method = lambda : 'HEAD'
  url = urllib2.urlopen(request).geturl()

  return (url, version)

def getOperaDownloadLink(galleryID):
  """
  gets download link for an Opera add-on from the Opera Addons site
  """
  galleryID = urlencode(galleryID)

  request = urllib2.Request('https://addons.opera.com/extensions/download/%s/' % galleryID)
  request.get_method = lambda : 'HEAD'
  response = urllib2.urlopen(request)

  content_disposition = response.info().getheader('Content-Disposition')
  if content_disposition:
    match = re.search(r'filename=\S+-([\d.]+)-\d+\.crx$', content_disposition)
    if match:
      return ('https://addons.opera.com/extensions/details/%s/' % galleryID , match.group(1))

  return (None, None)

def getLocalLink(repo):
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

def getDownloadLink(repo):
  """
  gets the download link to the most current version of an extension
  """
  # you can't easily install extensions from third-party sources on Chrome
  # and Opera. So always get the link for the version on the Web Store.
  if repo.galleryID:
    if repo.type == "chrome":
      return getGoogleDownloadLink(repo.galleryID)
    if repo.type == "opera":
      return getOperaDownloadLink(repo.galleryID)

  (localURL, localVersion) = getLocalLink(repo)

  # get a link to Firefox Add-Ons, if the latest version has been published there
  if repo.type == 'gecko' and repo.galleryID:
    (galleryURL, galleryVersion) = getMozillaDownloadLink(repo.galleryID)
    if not localVersion or (galleryVersion and
                            compareVersions(galleryVersion, localVersion) >= 0):
      return (galleryURL, galleryVersion)

  return (localURL, localVersion)

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

def readMetadata(repo, version):
  """
  reads extension ID and compatibility information from metadata file in the
  extension's repository
  """
  if repo.type == 'android':
    command = ['hg', '-R', repo.repository, 'id', '-r', version, '-n']
    result = subprocess.check_output(command)
    revision = re.sub(r'\D', '', result)

    return {
      'revision': revision,
      'minSdkVersion': get_min_sdk_version(repo, version),
    }
  elif repo.type == 'safari':
    metadata = repo.readMetadata(version)
    return {
      'certificateID': getSafariCertificateID(repo.keyFile),
      'version': version,
      'shortVersion': version,
      'basename': metadata.get('general', 'basename'),
    }
  elif repo.type == 'gecko':
    metadata = repo.readMetadata(version)
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

def writePadFile(links):
  for repo in Configuration.getRepositoryConfigurations():
    if repo.pad and links.has_section(repo.repositoryName):
      PadFile.forRepository(repo, links.get(repo.repositoryName, 'version'),
                                  links.get(repo.repositoryName, 'downloadURL')).write()

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
  writePadFile(result)

if __name__ == "__main__":
  updateLinks()
