# coding: utf-8
 
"""
Update the list of extenstions
==============================

  This script generates a list of extensions and saves these with download links 
  and version information
"""

import os, urllib, urlparse, subprocess
import xml.dom.minidom as dom
from ConfigParser import SafeConfigParser
from sitescripts.utils import get_config
from sitescripts.extensions.utils import compareVersions, Configuration

def urlencode(value):
  return urllib.quote(value.encode('utf-8'), '')

def getMozillaDownloadLink(galleryID):
  """
  gets download link for a Gecko add-on from the Mozilla Addons site
  """
  url = 'https://services.addons.mozilla.org/en-US/firefox/api/1/addon/%s' % urlencode(galleryID)
  contents = urllib.urlopen(url).read()
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
  contents = urllib.urlopen(url).read()
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

if __name__ == "__main__":
  updateLinks()
