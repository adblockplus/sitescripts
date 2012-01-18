# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import os, marshal
from sitescripts.utils import get_config, setupStderr
from sitescripts.reports.utils import saveReport

def scanDumps(dir):
  for file in os.listdir(dir):
    filePath = os.path.join(dir, file)
    if os.path.isdir(filePath):
      scanDumps(filePath)
    elif file.endswith('.dump'):
      processReport(filePath)

def processReport(filePath):
  guid = os.path.splitext(os.path.basename(filePath))[0]
  handle = open(filePath, 'rb')
  reportData = marshal.load(handle)
  handle.close()
  saveReport(guid, reportData)  
  os.remove(filePath)
     
if __name__ == '__main__':
  setupStderr()
  scanDumps(get_config().get('reports', 'dataPath'))
