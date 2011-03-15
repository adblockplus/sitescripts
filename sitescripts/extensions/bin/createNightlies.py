# coding: utf-8

"""

Nightly builds generation script
================================

  This script generates nightly builds of extensions, together
  with changelogs and documentation.

"""

import sys, os, os.path, subprocess, ConfigParser, traceback, json, hashlib
import tempfile, re, shutil, urlparse
from datetime import datetime
from sitescripts.utils import get_config, setupStderr, get_template
from sitescripts.extensions.utils import compareVersions, Configuration, KNOWN_APPS

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
    command = ["hg", "log", "-R", self.config.repository, "-b", "default", "-l", "1", "--template", "{node|short}"]
    (result, dummy) = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()
    return result

  def getChanges(self):
    """
      retrieve changes between the current and previous ("first") revision
    """

    command = ['hg', 'log', '-R', self.tempdir, '-b', 'default',
      '-l', '50', '-M',
      '--template', '{date|isodate}\\0{author|person}\\0{rev}\\0{desc}\\0\\0']
    (result, dummy) = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()

    for change in result.split('\0\0'):
      if change:
        date, author, revision, description = change.split('\0')
        yield {'date': date, 'author': author, 'revision': revision, 'description': description}

  def cloneRepository(self):
    """
      clone the repository into the tempdir
    """
    self.tempdir = tempfile.mkdtemp(prefix=self.config.repositoryName)
      
    command = ['hg', 'clone', '-q', '-U', self.config.repository, self.tempdir]
    subprocess.Popen(command).communicate()
      
    command = ['hg', 'up', '-q', '-R', self.tempdir, '-r', 'default']
    subprocess.Popen(command).communicate()

    try:
      command = ['hg', 'archive', '-q', '-R', self.config.buildRepository, '-r', 'default', os.path.join(self.tempdir, 'buildtools')]
      subprocess.Popen(command).communicate()
    except:
      pass

  def writeSignature(self):
    """
      write the signature file into the cloned repository
    """
    if self.config.type != 'gecko':
      # This step is only required for Mozilla extensions
      return

    try:
      if self.config.signtool:
        signatureFilename = os.path.join(self.tempdir, ".signature")
        f = open(signatureFilename, 'wb')
        print >>f, "signtool=%s" % self.config.signtool
        print >>f, "certname=%s" % self.config.certname
        print >>f, "dbdir=%s" % self.config.dbdir
        print >>f, "dbpass=%s" % self.config.dbpass
        f.close()
    except ConfigParser.NoOptionError:
      pass

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
      os.symlink(changelogPath, linkPath)
    else:
      shutil.copyfile(changelogPath, linkPath)

  def readMetadata(self):
    """
      read the metadata file from a cloned repository
      and parse id, version, basename and the compat section
      out of the file
    """
    filename = os.path.join(self.tempdir, "metadata")
    parser = ConfigParser.SafeConfigParser()
    parser.read(filename)
    
    self.extensionID = parser.get("general", "id")
    self.version = parser.get("general", "version")
    self.basename = parser.get("general", "basename")
    self.compat = []
    for key, value in KNOWN_APPS.iteritems():
      if parser.has_option('compat', key):
        minVersion, maxVersion = parser.get('compat', key).split('/')
        self.compat.append({'id': value, 'minVersion': minVersion, 'maxVersion': maxVersion})

  def readChromeMetadata(self):
    """
      Read Chrome-specific metadata from manifest.json file. It will also
      calculate extension ID from the private key.
    """

    # Calculate extension ID from public key
    # (see http://supercollider.dk/2010/01/calculating-chrome-extension-id-from-your-private-key-233)
    sys.path.append(self.tempdir)
    build = __import__('build')
    publicKey = build.getPublicKey(self.config.keyFile)
    hash = hashlib.sha256()
    hash.update(publicKey)
    self.extensionID = hash.hexdigest()[0:32]
    self.extensionID = ''.join(map(lambda c: chr(97 + int(c, 16)), self.extensionID))

    # Now read manifest.json
    manifestFile = open(os.path.join(self.tempdir, 'manifest.json'), 'rb')
    manifest = json.load(manifestFile)
    manifestFile.close()

    self.version = manifest['version']
    self.basename = os.path.basename(self.config.repository)
    self.compat = []
    if 'minimum_chrome_version' in manifest:
      self.compat.append({'id': 'chrome', 'minVersion': manifest['minimum_chrome_version']})

  def calculateBuildNumber(self):
    """
      calculate the effective nightly build number
    """
    if self.config.type == 'gecko' and not re.search(r'[^\d\.]\d*$', self.version):
      parts = self.version.split('.')
      while len(parts) < 3:
        parts.append('0')
      self.version = '.'.join(parts) + '+'
    self.buildNumber, dummy = subprocess.Popen(['hg', 'id', '-R', self.tempdir, '-n'], stdout=subprocess.PIPE).communicate()
    self.buildNumber = re.sub(r'\D', '', self.buildNumber)
    self.version += '.' + self.buildNumber

  def writeUpdateManifest(self):
    """
      Writes update.rdf file for the current build
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    if not os.path.exists(baseDir):
      os.makedirs(baseDir)
    if self.config.type != 'chrome':
      manifestPath = os.path.join(baseDir, "update.rdf")
      templateName = 'geckoUpdateManifest'
    else:
      manifestPath = os.path.join(baseDir, "updates.xml")
      templateName = 'chromeUpdateManifest'

    template = get_template(get_config().get('extensions', templateName))
    template.stream({'extensions': [self]}).dump(manifestPath)

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

    if self.config.type != 'chrome':
      currentPath = os.getcwd()
      try:
        os.chdir(self.tempdir)
        buildCommand = ['perl', 'create_xpi.pl', outputPath, self.buildNumber]
        subprocess.Popen(buildCommand, stdout=subprocess.PIPE).communicate()
      finally:
        os.chdir(currentPath)
    else:
      buildCommand = ['python', os.path.join(self.tempdir, 'build.py'), '-k', self.config.keyFile, outputPath]
      subprocess.Popen(buildCommand, stdout=subprocess.PIPE).communicate()

    if not os.path.exists(outputPath):
      raise Exception("Build failed, output file hasn't been created")

    linkPath = os.path.join(baseDir, '00latest%s' % self.config.packageSuffix)
    if hasattr(os, 'symlink'):
      if os.path.exists(linkPath):
        os.remove(linkPath)
      os.symlink(outputPath, linkPath)
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
    if not os.path.exists(os.path.join(self.tempdir, 'generateDocs.pl')):
      return

    outputPath = os.path.join(self.config.docsDirectory, self.basename)
    currentPath = os.getcwd()
    try:
      os.chdir(self.tempdir)
      buildCommand = ['perl', 'generateDocs.pl', outputPath]
      subprocess.Popen(buildCommand, stdout=subprocess.PIPE).communicate()
    finally:
      os.chdir(currentPath)

  def run(self):
    """
      Run the nightly build process for one extension
    """
    try:
      if self.config.type == 'kmeleon':
        # We cannot build K-Meleon builds, simply list the builds already in
        # the directory. Basename has to be deduced from the repository name.
        self.basename = os.path.basename(self.config.repository)
      else:
        # clone the repository to the tempdir
        self.cloneRepository()

        # write the signature file to the tempdir
        self.writeSignature()

        # get meta data from the repository
        if self.config.type != 'chrome':
          self.readMetadata()
        else:
          self.readChromeMetadata()

        # generate the current build number
        self.calculateBuildNumber()

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
