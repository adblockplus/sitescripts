# coding: utf-8

# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/

import os, ConfigParser, subprocess, tempfile, shutil
from sitescripts.utils import get_config, setupStderr

def splitRepositoryPath(path):
  repo = os.path.abspath(path)
  while not os.path.isdir(os.path.join(repo, '.hg')):
    if len(repo) < 4:
      raise Exception('Mercurial repository not found for path %s' % path)
    repo = os.path.basename(repo)
  return (repo, os.path.relpath(path, repo))

def chown((uid, gid), dirname, names):
  for name in names:
    os.chown(os.path.join(dirname, name), uid, gid)

def syncFiles(name, settings, syncState):
  repo, path = splitRepositoryPath(settings['source'])

  command = ['hg', 'log', '-R', repo, '-r', 'default', '--template', '{node|short}']
  currentRevision, dummy = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()

  if not syncState.has_section(name):
    syncState.add_section(name)
  if syncState.has_option(name, 'latestRevision') and currentRevision == syncState.get(name, 'latestRevision'):
    # Already up to date, nothing to do
    return

  tempdir = tempfile.mkdtemp(prefix=name)
  try:
    command = ['hg', 'archive', '-R', repo, '-r', 'default', '-X', os.path.join(repo, '.hg_archival.txt'), tempdir]
    subprocess.Popen(command, stdout=subprocess.PIPE).communicate()
    for relpath in settings['ignore']:
      abspath = os.path.join(tempdir, relpath)
      if os.path.commonprefix((abspath, tempdir)) == tempdir and os.path.exists(abspath):
        shutil.rmtree(abspath)

    if hasattr(os, 'chown') and settings['user'] and settings['group']:
      from pwd import getpwnam
      from grp import getgrnam
      uid = getpwnam(settings['user']).pw_uid
      gid = getgrnam(settings['group']).gr_gid
      os.path.walk(tempdir, chown, (uid, gid))
      os.chmod(tempdir, 0755)
      os.chown(tempdir, uid, gid)

    command = ['rsync', '-a', '--delete']
    for relpath in settings['ignore']:
      abspath = os.path.join(settings['target'], relpath)
      if os.path.commonprefix((abspath, settings['target'])) == settings['target'] and os.path.exists(abspath):
        command.append('--exclude')
        if os.path.isdir(abspath):
          command.append(os.path.join(relpath, '.')[0:-1])
        else:
          command.append(relpath)
    command.append(os.path.join(tempdir, '.')[0:-1])
    command.append(settings['target'])
    subprocess.Popen(command, stdout=subprocess.PIPE).communicate()

    if settings['postsync']:
      subprocess.Popen(settings['postsync'], stdout=subprocess.PIPE, shell=True).communicate()

    syncState.set(name, 'latestRevision', currentRevision)
  finally:
    shutil.rmtree(tempdir, ignore_errors=True)

def readSyncSettings():
  result = {}
  for option in get_config().options('filesync'):
    if option.find('_') < 0:
      continue
    name, setting = option.rsplit('_', 2)
    if not setting in ('source', 'target', 'user', 'group', 'ignore', 'postsync'):
      continue

    if not name in result:
      result[name] = {
        'source': None,
        'target': None,
        'user': None,
        'group': None,
        'postsync': None,
        'ignore': []
      }
    if isinstance(result[name][setting], list):
      result[name][setting] = get_config().get('filesync', option).split(' ')
    else:
      result[name][setting] = get_config().get('filesync', option)
  return result

if __name__ == '__main__':
  setupStderr()

  syncState = ConfigParser.SafeConfigParser()
  syncStateFile = get_config().get('filesync', 'syncData')
  if os.path.exists(syncStateFile):
    syncState.read(syncStateFile)

  settings = readSyncSettings()
  for name, value in settings.iteritems():
    syncFiles(name, value, syncState)

  file = open(syncStateFile, 'wb')
  syncState.write(file)
