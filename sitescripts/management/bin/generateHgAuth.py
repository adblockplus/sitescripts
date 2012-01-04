# coding: utf-8

# This Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.

import os, re, sys, subprocess, tarfile
from StringIO import StringIO
from sitescripts.utils import get_config, setupStderr

def generateData(authRepo):
  command = ['hg', '-R', authRepo, 'archive', '-r', 'default', '-t', 'tar', '-p', '.', '-']
  (data, dummy) = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()

  users = {}
  repos = []
  tarFile = tarfile.open(mode='r:', fileobj=StringIO(data))
  fileInfo = tarFile.next()
  while fileInfo:
    if fileInfo.type == tarfile.REGTYPE and fileInfo.name.startswith('users/'):
      name = os.path.basename(fileInfo.name).lower()
      options = []
      match = re.search(r'^(.*)\[(.*)\]$', name)
      if match:
        name = match.group(1)
        options = match.group(2).split(',')

      user = {
        'name': name,
        'keytype': 'rsa',
        'disabled': False,
        'trusted': False,
        'repos': []
      }
      for option in options:
        if option == 'dsa':
          user['keytype'] = 'dsa'
        elif option == 'disabled':
          user['disabled'] = True
        elif option == 'trusted':
          user['trusted'] = True
        else:
          print >>sys.stderr, 'Unknown user option: %s' % option
      user['key'] = re.sub(r'\s', '', tarFile.extractfile(fileInfo).read())
      users[name] = user
    elif fileInfo.type == tarfile.REGTYPE and fileInfo.name.startswith('repos/'):
      repos.append(fileInfo)
    elif fileInfo.type == tarfile.REGTYPE and not fileInfo.name.startswith('.'):
      print >>sys.stderr, 'Unrecognized file in the repository: %s' % fileInfo.name
    fileInfo = tarFile.next()

  for fileInfo in repos:
    name = os.path.basename(fileInfo.name).lower()
    repoUsers = tarFile.extractfile(fileInfo).readlines()
    for user in repoUsers:
      user = user.strip()
      if user == '' or user.startswith('#'):
        continue
      if user in users:
        users[user]['repos'].append(name)
      else:
        print >>sys.stderr, 'Unknown user listed for repository %s: %s' % (name, user)

  for user in users.itervalues():
    if user['disabled']:
      continue
    yield 'no-pty,environment="HGUSER=%s",environment="HGREPOS=%s" %s %s\n' % (
      user['name'] if not user['trusted'] else '',
      ' '.join(user['repos']),
      'ssh-rsa' if user['keytype'] == 'rsa' else 'ssh-dss',
      user['key']
    )

def hook(ui, repo, **kwargs):
  setupStderr()

  result = generateData(get_config().get('hg', 'auth_repository'))

  file = open(get_config().get('hg', 'auth_file'), 'wb')
  for s in result:
    file.write(s)
  file.close()

if __name__ == '__main__':
  hook()
