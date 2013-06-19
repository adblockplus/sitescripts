# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2013 Eyeo GmbH
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

Nightly builds generation script
================================

  This script generates nightly builds of extensions, together
  with changelogs and documentation.

"""

import sys, os, os.path, codecs, subprocess, ConfigParser, traceback, json, hashlib
import tempfile, re, shutil, urlparse, pipes
from datetime import datetime
from xml.dom.minidom import parse as parseXml
from sitescripts.utils import get_config, setupStderr, get_template
from sitescripts.extensions.utils import compareVersions, Configuration

MAX_BUILDS = 50


class NightlyBuild(object):
  """
    Performs the build process for an extension,
    generating changelogs and documentation.
  """

  def __init__(self, config):
    """
      Creates a NightlyBuild instance; we are simply
      recording the configuration settings here.
    """
    self.config = config
    self.revision = self.getCurrentRevision()
    try:
      self.previousRevision = config.latestRevision
    except:
      self.previousRevision = '0'
    self.tempdir = None
    self.outputFilename = None
    self.changelogFilename = None

  def hasChanges(self):
    return self.revision != self.previousRevision

  def getCurrentRevision(self):
    """
      retrieves the current revision number from the repository
    """
    command = ['hg', 'log', '-R', self.config.repository, '-r', 'default', '--template', '{rev}']
    (result, dummy) = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()
    return result

  def getChanges(self):
    """
      retrieve changes between the current and previous ("first") revision
    """

    command = ['hg', 'log', '-R', self.config.repository, '-r', 'tip:0',
      '-b', 'default', '-l', '50',
      '--template', '{date|isodate}\\0{author|person}\\0{rev}\\0{desc}\\0\\0']
    (result, dummy) = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()

    for change in result.split('\0\0'):
      if change:
        date, author, revision, description = change.split('\0')
        yield {'date': date, 'author': author, 'revision': revision, 'description': description}

  def copyRepository(self):
    '''
      Create a repository copy in a temporary directory
    '''
    # We cannot use hg archive here due to
    # http://bz.selenic.com/show_bug.cgi?id=3747, have to clone properly :-(
    self.tempdir = tempfile.mkdtemp(prefix=self.config.repositoryName)
    command = ['hg', 'clone', '-q', self.config.repository, '-u', 'default', self.tempdir]
    subprocess.Popen(command).communicate()

  def writeChangelog(self, changes):
    """
      write the changelog file into the cloned repository
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    if not os.path.exists(baseDir):
      os.makedirs(baseDir)
    changelogFile = "%s-%s.changelog.xhtml" % (self.basename, self.version)
    changelogPath = os.path.join(baseDir, changelogFile)
    self.changelogURL = urlparse.urljoin(self.config.nightliesURL, self.basename + '/' + changelogFile)

    template = get_template(get_config().get('extensions', 'changelogTemplate'))
    template.stream({'changes': changes}).dump(changelogPath)

    linkPath = os.path.join(baseDir, '00latest.changelog.xhtml')
    if hasattr(os, 'symlink'):
      if os.path.exists(linkPath):
        os.remove(linkPath)
      os.symlink(os.path.basename(changelogPath), linkPath)
    else:
      shutil.copyfile(changelogPath, linkPath)

  def readMetadata(self):
    """
      read the metadata file from a cloned repository
      and parse id, version, basename and the compat section
      out of the file
    """
    import buildtools.packagerGecko as packager
    metadata = packager.readMetadata(self.tempdir)
    self.extensionID = metadata.get("general", "id")
    self.version = packager.getBuildVersion(self.tempdir, metadata, False, self.revision)
    self.basename = metadata.get("general", "basename")
    self.compat = []
    for key, value in packager.KNOWN_APPS.iteritems():
      if metadata.has_option('compat', key):
        minVersion, maxVersion = metadata.get('compat', key).split('/')
        self.compat.append({'id': value, 'minVersion': minVersion, 'maxVersion': maxVersion})

  def readAndroidMetadata(self):
    """
      Read Android-specific metadata from AndroidManifest.xml file.
    """
    manifestFile = open(os.path.join(self.tempdir, 'AndroidManifest.xml'), 'r')
    manifest = parseXml(manifestFile)
    manifestFile.close()

    root = manifest.documentElement
    self.version = root.attributes["android:versionName"].value
    while self.version.count('.') < 2:
      self.version += '.0'
    self.version = '%s.%s' % (self.version, self.revision)

    usesSdk = manifest.getElementsByTagName('uses-sdk')[0]
    self.minSdkVersion = usesSdk.attributes["android:minSdkVersion"].value
    self.basename = os.path.basename(self.config.repository)

  def readChromeMetadata(self):
    """
      Read Chrome-specific metadata from metadata file. This will also
      calculate extension ID from the private key.
    """

    # Calculate extension ID from public key
    # (see http://supercollider.dk/2010/01/calculating-chrome-extension-id-from-your-private-key-233)
    import buildtools.packagerChrome as packager
    publicKey = packager.getPublicKey(self.config.keyFile)
    hash = hashlib.sha256()
    hash.update(publicKey)
    self.extensionID = hash.hexdigest()[0:32]
    self.extensionID = ''.join(map(lambda c: chr(97 + int(c, 16)), self.extensionID))

    # Now read metadata file
    metadata = packager.readMetadata(self.tempdir, self.config.type)
    self.version = packager.getBuildVersion(self.tempdir, metadata, False, self.revision)
    self.basename = metadata.get("general", "basename")
    if self.config.experimental:
      self.basename += '-experimental'

    self.compat = []
    if metadata.has_section('compat') and metadata.has_option('compat', 'chrome'):
      self.compat.append({'id': 'chrome', 'minVersion': metadata.get('compat', 'chrome')})

  def writeUpdateManifest(self):
    """
      Writes update.rdf file for the current build
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    if not os.path.exists(baseDir):
      os.makedirs(baseDir)
    if self.config.type == 'chrome' or self.config.type == 'opera':
      manifestPath = os.path.join(baseDir, "updates.xml")
      templateName = 'chromeUpdateManifest'
    elif self.config.type == 'android':
      manifestPath = os.path.join(baseDir, "updates.xml")
      templateName = 'androidUpdateManifest'
    else:
      manifestPath = os.path.join(baseDir, "update.rdf")
      templateName = 'geckoUpdateManifest'

    template = get_template(get_config().get('extensions', templateName))
    template.stream({'extensions': [self]}).dump(manifestPath)

  def writeLibabpUpdateManifest(self, updates):
    """
      Writes update.json file for libadblockplus
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    if not os.path.exists(baseDir):
      os.makedirs(baseDir)
    manifestPath = os.path.join(baseDir, "update.json")

    handle = codecs.open(manifestPath, "wb", encoding="UTF-8")
    json.dump(updates, handle, ensure_ascii=False, indent=2, separators=(",", ": "))
    handle.close()

  def writeIEUpdateManifest(self, versions):
    """
      Writes update.json file for the latest IE build
    """
    if len(versions) == 0:
      return

    version = versions[0]
    packageName = self.basename + '-' + versions[0] + self.config.packageSuffix
    updateURL = urlparse.urljoin(self.config.nightliesURL, self.basename + '/' + packageName + '?update')
    self.writeLibabpUpdateManifest({
      "%s/%s" % (self.basename, "msie64"): {
        "url": updateURL,
        "version": version,
      },
      "%s/%s" % (self.basename, "win64"): {
        "url": updateURL,
        "version": version,
      },
      "%s/%s" % (self.basename, "msie32"): {
        "url": updateURL.replace("-x64", "-x86"),
        "version": version,
      },
      "%s/%s" % (self.basename, "win32"): {
        "url": updateURL.replace("-x64", "-x86"),
        "version": version,
      },
    })

    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    for suffix in (self.config.packageSuffix, self.config.packageSuffix.replace("-x64", "-x86")):
      linkPath = os.path.join(baseDir, '00latest%s' % suffix)
      outputPath = os.path.join(baseDir, self.basename + '-' + versions[0] + suffix)
      if hasattr(os, 'symlink'):
        if os.path.exists(linkPath):
          os.remove(linkPath)
        os.symlink(os.path.basename(outputPath), linkPath)
      else:
        shutil.copyfile(outputPath, linkPath)


  def build(self):
    """
      run the build command in the tempdir
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    if not os.path.exists(baseDir):
      os.makedirs(baseDir)
    outputFile = "%s-%s%s" % (self.basename, self.version, self.config.packageSuffix)
    outputPath = os.path.join(baseDir, outputFile)
    self.updateURL = urlparse.urljoin(self.config.nightliesURL, self.basename + '/' + outputFile + '?update')

    if self.config.type == 'android':
      apkFile = open(outputPath, 'wb')
      try:
        port = get_config().get('extensions', 'androidBuildPort')
      except ConfigParser.NoOptionError:
        port = '22'
      buildCommand = ['ssh', '-p', port, get_config().get('extensions', 'androidBuildHost')]
      buildCommand += map(pipes.quote, ['/home/android/bin/makedebugbuild.py', '--revision', self.revision, '--version', self.version, '--stdout'])
      process = subprocess.Popen(buildCommand, stdout=apkFile, stderr=None)
      status = process.wait()
      apkFile.close()
      if status:
        # clear broken output if any
        # exception will be raised later
        if os.path.exists(outputPath):
          os.remove(outputPath)
    elif self.config.type == 'chrome' or self.config.type == 'opera':
      import buildtools.packagerChrome as packager
      packager.createBuild(self.tempdir, type=self.config.type, outFile=outputPath, buildNum=self.revision, keyFile=self.config.keyFile, experimentalAPI=self.config.experimental)
    else:
      import buildtools.packagerGecko as packager
      packager.createBuild(self.tempdir, outFile=outputPath, buildNum=self.revision, keyFile=self.config.keyFile)

    if not os.path.exists(outputPath):
      raise Exception("Build failed, output file hasn't been created")

    linkPath = os.path.join(baseDir, '00latest%s' % self.config.packageSuffix)
    if hasattr(os, 'symlink'):
      if os.path.exists(linkPath):
        os.remove(linkPath)
      os.symlink(os.path.basename(outputPath), linkPath)
    else:
      shutil.copyfile(outputPath, linkPath)

  def retireBuilds(self):
    """
      removes outdated builds, returns the sorted version numbers of remaining
      builds
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    versions = []
    prefix = self.basename + '-'
    suffix = self.config.packageSuffix
    for fileName in os.listdir(baseDir):
      if fileName.startswith(prefix) and fileName.endswith(suffix):
        versions.append(fileName[len(prefix):len(fileName) - len(suffix)])
    versions.sort(compareVersions, reverse = True)
    while len(versions) > MAX_BUILDS:
      version = versions.pop()
      os.remove(os.path.join(baseDir, prefix + version + suffix))
      changelogPath = os.path.join(baseDir, prefix + version + '.changelog.xhtml')
      if os.path.exists(changelogPath):
        os.remove(changelogPath)
    return versions

  def updateIndex(self, versions):
    """
      Updates index page listing all existing versions
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    if not os.path.exists(baseDir):
      os.makedirs(baseDir)
    outputFile = "index.html"
    outputPath = os.path.join(baseDir, outputFile)

    links = []
    for version in versions:
      packageFile = self.basename + '-' + version + self.config.packageSuffix
      changelogFile = self.basename + '-' + version + '.changelog.xhtml'
      if not os.path.exists(os.path.join(baseDir, packageFile)):
        # Oops
        continue

      link = {
        'version': version,
        'download': packageFile,
        'mtime': os.path.getmtime(os.path.join(baseDir, packageFile)),
        'size': os.path.getsize(os.path.join(baseDir, packageFile))
      }
      if os.path.exists(os.path.join(baseDir, changelogFile)):
        link['changelog'] = changelogFile
      links.append(link)
    template = get_template(get_config().get('extensions', 'nightlyIndexPage'))
    template.stream({'config': self.config, 'links': links}).dump(outputPath)

  def updateDocs(self):
    if not self.config.type == 'gecko':
      return

    docsdir = tempfile.mkdtemp(prefix='jsdoc')
    command = ['hg', 'archive', '-R', get_config().get('extensions', 'jsdocRepository'), '-r', 'default', docsdir]
    subprocess.Popen(command).communicate()

    try:
      outputPath = os.path.join(self.config.docsDirectory, self.basename)
      command = ['perl', os.path.join(docsdir, 'jsrun.pl'),
        '-t=' + os.path.join(docsdir, 'templates', 'jsdoc'),
        '-d=' + outputPath,
        '-a',
        '-p',
        '-x=js',
        os.path.join(self.tempdir, 'lib')]
      subprocess.Popen(command, stdout=subprocess.PIPE).communicate()
    finally:
      shutil.rmtree(docsdir, ignore_errors=True)

  def run(self):
    """
      Run the nightly build process for one extension
    """
    try:
      if self.config.type == 'ie':
        # We cannot build IE builds, simply list the builds already in
        # the directory. Basename has to be deduced from the repository name.
        self.basename = os.path.basename(self.config.repository)
      else:
        # copy the repository into a temporary directory
        self.copyRepository()

        # get meta data from the repository
        if self.config.type == 'android':
          self.readAndroidMetadata()
        elif self.config.type == 'chrome' or self.config.type == 'opera':
          self.readChromeMetadata()
        else:
          self.readMetadata()

        # create development build
        self.build()

        # write out changelog
        self.writeChangelog(self.getChanges())

        # write update.rdf file
        self.writeUpdateManifest()

        # update documentation
        self.updateDocs()

      # retire old builds
      versions = self.retireBuilds()

      if self.config.type == 'ie':
        self.writeIEUpdateManifest(versions)

      # update index page
      self.updateIndex(versions)

      # update nightlies config
      self.config.latestRevision = self.revision
    finally:
      # clean up
      if self.tempdir:
        shutil.rmtree(self.tempdir, ignore_errors=True)


def main():
  """
    main function for createNightlies.py
  """
  setupStderr()

  nightlyConfig = ConfigParser.SafeConfigParser()
  nightlyConfigFile = get_config().get('extensions', 'nightliesData')
  if os.path.exists(nightlyConfigFile):
    nightlyConfig.read(nightlyConfigFile)

  # build all extensions specified in the configuration file
  # and generate changelogs and documentations for each:
  data = None
  for repo in Configuration.getRepositoryConfigurations(nightlyConfig):
    build = None
    try:
      build = NightlyBuild(repo)
      if build.hasChanges():
        build.run()
    except Exception, ex:
      print >>sys.stderr, "The build for %s failed:" % repo
      traceback.print_exc()

  file = open(nightlyConfigFile, 'wb')
  nightlyConfig.write(file)


if __name__ == '__main__':
  main()
