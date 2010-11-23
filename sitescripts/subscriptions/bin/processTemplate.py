# coding: utf-8

import sys
from sitescripts.utils import get_config, get_template, setupStderr
import sitescripts.subscriptions.subscriptionParser as subscriptionParser

if __name__ == '__main__':
  setupStderr()

  if len(sys.argv) < 2:
    raise Exception('A template like recommendations, subscriptionList or subscriptionsXML needs to be specified on command line')
  
  subscriptions = subscriptionParser.readSubscriptions().values()
  template = get_template(get_config().get('subscriptions', sys.argv[1] + 'Template'))
  if len(sys.argv) >= 3:
    outputFile = sys.argv[2]
  else:
    outputFile = get_config().get('subscriptions', sys.argv[1] + 'File')
  template.stream({'subscriptions': subscriptions}).dump(outputFile, encoding='utf-8')
