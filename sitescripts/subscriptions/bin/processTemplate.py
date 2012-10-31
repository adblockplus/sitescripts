# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2012 Eyeo GmbH
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

import sys
from sitescripts.utils import get_config, get_template, setupStderr
import sitescripts.subscriptions.subscriptionParser as subscriptionParser

def writeSubscriptions(templateName, outputFile=None):
  subscriptions = subscriptionParser.readSubscriptions().values()
  template = get_template(get_config().get('subscriptions', templateName + 'Template'))
  if outputFile == None:
    outputFile = get_config().get('subscriptions', templateName + 'File')
  template.stream({'subscriptions': subscriptions}).dump(outputFile, encoding='utf-8')

if __name__ == '__main__':
  setupStderr()

  if len(sys.argv) < 2:
    raise Exception('A template like recommendations, subscriptionList, subscriptionsXML or subscriptionsXML2 needs to be specified on command line')

  templateName = sys.argv[1]
  outputFile = None
  if len(sys.argv) >= 3:
    outputFile = sys.argv[2]
  writeSubscriptions(templateName, outputFile)
