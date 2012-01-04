# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import os, re, subprocess, tempfile, shutil
from sitescripts.utils import get_config, setupStderr

if __name__ == '__main__':
  setupStderr()

  source = get_config().get('subscriptionDownloads', 'outdir')
  cvsroot = get_config().get('subscriptionDownloads', 'cvsroot')
  cvsdir = get_config().get('subscriptionDownloads', 'cvsdir')
  dest = tempfile.mkdtemp()
  try:
    os.chdir(os.path.dirname(dest))   # Yes, CVS sucks
    subprocess.Popen(['cvs', '-Q', '-d', cvsroot, 'checkout', '-d', os.path.basename(dest), cvsdir]).communicate()
    os.chdir(dest)
    (result, dummy) = subprocess.Popen(['rsync', '-a', '--delete', '--out-format=%o %n', '--exclude=CVS', source + '/', dest], stdout=subprocess.PIPE).communicate()
    for line in result.split('\n'):
      match = re.search(r'^(\S+)\s+(.*)', line)
      if match and match.group(1) == 'send':
        subprocess.Popen(['cvs', '-Q', 'add', match.group(2)]).communicate()
      elif match and match.group(1) == 'del.':
        subprocess.Popen(['cvs', '-Q', 'remove', match.group(2)]).communicate()
    subprocess.Popen(['cvs', '-Q', 'commit', '-m', 'Uploading subscription updates'], stdout=subprocess.PIPE).communicate()
  finally:
    if os.path.exists(dest):
      shutil.rmtree(dest, True)
