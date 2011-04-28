# coding: utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

import os, re, subprocess, tempfile, shutil
from sitescripts.utils import get_config, setupStderr

if __name__ == '__main__':
  setupStderr()

  source = get_config().get('easylist', 'outdir')
  cvsroot = get_config().get('easylist', 'cvsroot')
  cvsdir = get_config().get('easylist', 'cvsdir')
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
