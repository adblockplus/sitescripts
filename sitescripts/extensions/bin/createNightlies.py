# coding: utf-8

"""

Nightly builds generation script
================================

  This script generates nightly builds of extensions, together
  with changelogs and documentation.

"""

import sys, os, os.path, subprocess, ConfigParser, traceback
import tempfile, re, shutil, urlparse
from datetime import datetime
from sitescripts.utils import get_config, setupStderr, get_template
from sitescripts.extensions.utils import compareVersions

MAX_BUILDS = 50

KNOWN_APPS = {
  'conkeror':   '{a79fe89b-6662-4ff4-8e88-09950ad4dfde}',
  'emusic':     'dlm@emusic.com',
  'fennec':     '{a23983c0-fd0e-11dc-95ff-0800200c9a66}',
  'firefox':    '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}',
  'midbrowser':   '{aa5ca914-c309-495d-91cf-3141bbb04115}',
  'prism':    'prism@developer.mozilla.org',
  'seamonkey':  '{92650c4d-4b8e-4d2a-b7eb-24ecf4f6b63a}',
  'songbird':   'songbird@songbirdnest.com',
  'thunderbird':  '{3550f703-e582-4d05-9a08-453d09bdfdc6}',
  'toolkit':    'toolkit@mozilla.org',
}


class Configuration(object):
  """
    This class represents the configuration settings for a single repository.
    Some of these properties come from the nightly config file and can be
    changed (latestRevision), others come from the global config and are
    read-only (repository, repositoryName, nightliesDirectory).
  """
  
  def _defineGlobalProperty(key):
    """
      Creates a property corresponding with a key in the nightly config file
    """
    return property(lambda self: self.config.get('extensions', key))

  def _defineNightlyProperty(key):
    """
      Creates a property corresponding with a key in the nightly config file
    """
    return property(lambda self: self.nightlyConfig.get(self.repositoryName, key),
                    lambda self, value: self.nightlyConfig.set(self.repositoryName, key, value))

  config = None
  nightlyConfig = None
  repositoryName = None
  repository = None

  nightliesDirectory = _defineGlobalProperty('nightliesDirectory')
  nightliesURL = _defineGlobalProperty('nightliesURL')
  docsDirectory = _defineGlobalProperty('docsDirectory')
  signtool = _defineGlobalProperty('signtool')
  certname = _defineGlobalProperty('signtool_certname')
  dbdir = _defineGlobalProperty('signtool_dbdir')
  dbpass = _defineGlobalProperty('signtool_dbpass')

  latestRevision = _defineNightlyProperty('latestRevision')

  def __init__(self, config, nightlyConfig, repositoryName, repository):
    """
      Creates a new Configuration instance that is bound to a particular
      repository.
    """

    self.repositoryName = repositoryName
    self.repository = repository
    self.config = config
    self.nightlyConfig = nightlyConfig
    if not self.nightlyConfig.has_section(self.repositoryName):
      self.nightlyConfig.add_section(self.repositoryName)

  def __str__(self):
    """
      Provides a string representation of this configuration
    """
    return self.repositoryName

  @staticmethod
  def getRepositoryConfigurations(config, nightlyConfig):
    """
      Retrieves configuration settings for all repositories
      from the configuration file, where existing repositories
      are identified by an <id>_repository entry appearing
      in the configuration file.
      This static method will enumerate Configuration
      objects representing the settings for each repository.
    """
    for key, value in config.items("extensions"):
      if key.endswith("_repository"):
        repositoryName = re.sub(r'_repository$', '', key)
        if repositoryName:
          yield Configuration(config, nightlyConfig, repositoryName, value)


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
    
  def writeSignature(self):
    """
      write the signature file into the cloned repository
    """
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

  def calculateBuildNumber(self):
    """
      calculate the effective nightly build number
    """
    if not re.search(r'[^\d\.]\d*$', self.version):
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
    manifestPath = os.path.join(baseDir, "update.rdf")

    template = get_template(get_config().get('extensions', 'geckoUpdateManifest'))
    template.stream({'build': self}).dump(manifestPath)

  def build(self):
    """
      run the build command in the tempdir
    """
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    if not os.path.exists(baseDir):
      os.makedirs(baseDir)
    outputFile = "%s-%s.xpi" % (self.basename, self.version)
    outputPath = os.path.join(baseDir, outputFile)
    self.updateURL = urlparse.urljoin(self.config.nightliesURL, self.basename + '/' + outputFile + '?update')

    currentPath = os.getcwd()
    try:
      os.chdir(self.tempdir)
      buildCommand = ['perl', 'create_xpi.pl', outputPath, self.buildNumber]
      subprocess.Popen(buildCommand, stdout=subprocess.PIPE).communicate()
    finally:
      os.chdir(currentPath)

    linkPath = os.path.join(baseDir, '00latest.xpi')
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
    suffix = '.xpi'
    for fileName in os.listdir(baseDir):
      if fileName.startswith(prefix) and fileName.endswith(suffix):
        versions.append(fileName[len(prefix):len(fileName) - len(suffix)])
    versions.sort(compareVersions, reverse = True)
    while len(versions) > MAX_BUILDS:
      version = versions.pop()
      os.remove(os.path.join(baseDir, prefix + version + suffix))
      os.remove(os.path.join(baseDir, prefix + version + '.changelog.xhtml'))
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
      packageFile = self.basename + '-' + version + '.xpi'
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
    template.stream({'name': self.basename, 'links': links}).dump(outputPath)

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
      # clone the repository to the tempdir
      self.cloneRepository()

      # write the signature file to the tempdir
      self.writeSignature()

      # get meta data from the repository
      self.readMetadata()

      # generate the current build number
      self.calculateBuildNumber()

      # create development build
      self.build()

      # write out changelog
      self.writeChangelog(self.getChanges())

      # write update.rdf file
      self.writeUpdateManifest()

      # retire old builds
      versions = self.retireBuilds()

      # update index page
      self.updateIndex(versions)

      # update documentation
      self.updateDocs()

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
  config = get_config()

  nightlyConfig = ConfigParser.SafeConfigParser()
  nightlyConfigFile = config.get('extensions', 'nightliesData')
  if os.path.exists(nightlyConfigFile):
    nightlyConfig.read(nightlyConfigFile)

  # build all extensions specified in the configuration file
  # and generate changelogs and documentations for each:
  data = None
  for repo in Configuration.getRepositoryConfigurations(config, nightlyConfig):
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
