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

"""
Generate update manifests
=========================

  This script generates update manifests for all extensions and apps
"""

import os
import re
import sys
import subprocess
import xml.dom.minidom as dom
from ConfigParser import SafeConfigParser

from sitescripts.extensions.bin.legacy.packagerSafari import get_developer_identifier
from sitescripts.extensions.bin.legacy.xarfile import read_certificates_and_key

from sitescripts.utils import get_config, get_template
from sitescripts.extensions.utils import (
    Configuration, getDownloadLinks,
    writeIEUpdateManifest, writeAndroidUpdateManifest)


def get_min_sdk_version(repo, version):
    command = ['hg', 'cat', '-r', version, 'AndroidManifest.xml']
    result = subprocess.check_output(command, cwd=repo.repository)
    uses_sdk = dom.parseString(result).getElementsByTagName('uses-sdk')[0]
    return uses_sdk.attributes['android:minSdkVersion'].value


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
        certs = read_certificates_and_key(repo.keyFile)[0]

        return {
            'certificateID': get_developer_identifier(certs),
            'version': version,
            'shortVersion': version,
            'basename': metadata.get('general', 'basename'),
            'updatedFromGallery': True
        }
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

    extensions = {'android': [], 'safari': [], 'ie': []}
    for repo in Configuration.getRepositoryConfigurations():
        if repo.type not in extensions or not links.has_section(repo.repositoryName):
            continue
        data = readMetadata(repo, links.get(repo.repositoryName, 'version'))
        data['updateURL'] = links.get(repo.repositoryName, 'downloadURL')
        if data['updateURL'].startswith(repo.downloadsURL):
            data['updateURL'] += '?update'
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
                newManifestPath = get_config().get('extensions',
                                                   'androidNewUpdateManifestPath')
                writeAndroidUpdateManifest(newManifestPath, extensions[repoType])
            path = get_config().get('extensions', '%sUpdateManifest' % repoType)
            template = get_template(path, autoescape=not path.endswith('.json'))
            template.stream({'extensions': extensions[repoType]}).dump(manifestPath)


def updateUpdateManifests():
    """
    updates all update manifests with the current versions
    """

    parser = SafeConfigParser()
    getDownloadLinks(parser)
    writeUpdateManifest(parser)


if __name__ == '__main__':
    updateUpdateManifests()
