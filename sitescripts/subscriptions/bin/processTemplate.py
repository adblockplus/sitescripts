# coding: utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

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
    raise Exception('A template like recommendations, subscriptionList or subscriptionsXML needs to be specified on command line')
  
  templateName = sys.argv[1]
  outputFile = None
  if len(sys.argv) >= 3:
    outputFile = sys.argv[2]
  writeSubscriptions(templateName, outputFile)
