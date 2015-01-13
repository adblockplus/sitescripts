# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
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
import xml.dom.minidom as dom

ANDROID_VERSIONS = ['1.0', '1.1', '1.5', '1.6', '2.0', '2.0.1', '2.1',
                    '2.2', '2.3', '2.3.3', '3.0', '3.1', '3.2', '4.0',
                    '4.0.3', '4.1', '4.2', '4.3', '4.4']

def get_min_sdk_version(repo, version):
  command = ['hg', 'cat', '-r', version, 'AndroidManifest.xml']
  result = subprocess.check_output(command, cwd=repo.repository)

  uses_sdk = dom.parseString(result).getElementsByTagName('uses-sdk')[0]
  return uses_sdk.attributes["android:minSdkVersion"].value

def get_min_android_version(repo, version):
  return ANDROID_VERSIONS[int(get_min_sdk_version(repo, version)) - 1]
