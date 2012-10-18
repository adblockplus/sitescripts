# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

"""
Update the list of extenstions
==============================

  This script generates a list of extensions and saves these with download links
  and version information
"""

import os, urllib, urlparse, subprocess, time
import xml.dom.minidom as dom
from ConfigParser import SafeConfigParser
from StringIO import StringIO
from sitescripts.utils import get_config, get_template
from sitescripts.extensions.utils import compareVersions, Configuration
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

def getLocalLink(repo):
  """
  gets the link for the newest download of an add-on in the local downloads
  repository
  """
  dir = repo.downloadsDirectory
  url = repo.downloadsURL

  highestURL = None
  highestVersion = None
  prefix = os.path.basename(repo.repository) + '-'
  suffix = repo.packageSuffix

  # go through the downloads directory looking for downloads matching this extension
  for fileName in os.listdir(dir):
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

  (downloadsURL, downloadsVersion) = getLocalLink(repo)
  if galleryVersion == None or (downloadsVersion != None and
                                compareVersions(galleryVersion, downloadsVersion) < 0):
    return (downloadsURL, downloadsVersion)
  else:
    return (galleryURL, galleryVersion)

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

def readMetadata(repo, version):
  """
  reads extension ID and compatibility information from metadata file in the
  extension's repository
  """
  command = ['hg', '-R', repo.repository, 'cat', '-r', version, os.path.join(repo.repository, 'metadata')]
  (result, dummy) = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()

  parser = SafeConfigParser()
  parser.readfp(StringIO(result))

  result = {
    'extensionID': parser.get('general', 'id'),
    'version': version,
    'compat': []
  }
  for key, value in KNOWN_APPS.iteritems():
    if parser.has_option('compat', key):
      minVersion, maxVersion = parser.get('compat', key).split('/')
      result['compat'].append({'id': value, 'minVersion': minVersion, 'maxVersion': maxVersion})
  return result

def writeUpdateManifest(links):
  """
  writes an update.rdf file for all Gecko extensions
  """

  extensions = []
  for repo in Configuration.getRepositoryConfigurations():
    if repo.type != 'gecko':
      continue
    if not links.has_section(repo.repositoryName):
      continue
    data = readMetadata(repo, links.get(repo.repositoryName, 'version'))
    data['updateURL'] = links.get(repo.repositoryName, 'downloadURL')
    extensions.append(data)

  manifestPath = get_config().get('extensions', 'geckoUpdateManifestPath')
  template = get_template(get_config().get('extensions', 'geckoUpdateManifest'))
  template.stream({'extensions': extensions}).dump(manifestPath)

def updateLinks():
  """
  writes the current extension download links to a file
  """

  # Update downloads directory first
  downloadsRepository = get_config().get('extensions', 'downloadsDirectory')
  subprocess.Popen(['hg', '-R', downloadsRepository, 'pull',  '-u'], stdout=subprocess.PIPE).communicate()

  # Now get download links and save them to file
  result = SafeConfigParser()
  getDownloadLinks(result)
  file = open(get_config().get('extensions', 'downloadLinksFile'), 'wb')
  result.write(file)
  file.close()

  writeUpdateManifest(result)

if __name__ == "__main__":
  updateLinks()
