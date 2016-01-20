# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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

from ConfigParser import SafeConfigParser
from sitescripts.utils import get_config
from sitescripts.extensions.utils import Configuration, getDownloadLinks
from sitescripts.extensions.pad import PadFile

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

  writePadFile(result)

if __name__ == "__main__":
  updateLinks()
