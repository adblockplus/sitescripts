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
Generate update manifests
=========================

  This script generates update manifests for all extensions and apps
"""

import os
import re
import subprocess
from buildtools.packagerGecko import KNOWN_APPS
from ConfigParser import SafeConfigParser
from sitescripts.utils import get_config, get_template
from sitescripts.extensions.utils import (
  Configuration, getDownloadLinks, getSafariCertificateID,
  writeIEUpdateManifest, writeAndroidUpdateManifest)
from sitescripts.extensions.android import get_min_sdk_version

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
      'version': version,
      'minSdkVersion': get_min_sdk_version(repo, version),
      'basename': os.path.basename(repo.repository)
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
  elif repo.type == 'ie':
    return {
      'version': version,
      'basename': os.path.basename(repo.repository)
    }
  else:
    raise Exception('unknown repository type %r' % repo.type)

def writeUpdateManifest(links):
  """
  writes an update manifest for all extensions and Android apps
  """

  extensions = {'gecko': [], 'android': [], 'safari': [], 'ie': []}
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
    if repoType == 'ie':
      writeIEUpdateManifest(manifestPath, extensions[repoType])
    else:
      # ABP for Android used to have its own update manifest format. We need to
      # generate both that and the new one in the libadblockplus format as long
      # as a significant amount of users is on an old version.
      if repoType == 'android':
        newManifestPath = get_config().get("extensions",
                                           "androidNewUpdateManifestPath")
        writeAndroidUpdateManifest(newManifestPath, extensions[repoType])
      template = get_template(get_config().get('extensions', '%sUpdateManifest' % repoType))
      template.stream({'extensions': extensions[repoType]}).dump(manifestPath)

def updateUpdateManifests():
  """
  updates all update manifests with the current versions
  """

  parser = SafeConfigParser()
  getDownloadLinks(parser)
  writeUpdateManifest(parser)

if __name__ == "__main__":
  updateUpdateManifests()
