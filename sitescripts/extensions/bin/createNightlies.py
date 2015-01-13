# coding: utf-8

# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2015 Eyeo GmbH
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

import sys, os, os.path, subprocess, ConfigParser, traceback, json, hashlib
import tempfile, shutil, urlparse, pipes, time, urllib2, struct
from datetime import datetime
from urllib import urlencode
from xml.dom.minidom import parse as parseXml
from sitescripts.utils import get_config, setupStderr, get_template
from sitescripts.extensions.utils import (
  compareVersions, Configuration, getSafariCertificateID,
  writeAndroidUpdateManifest)

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
    command = ['hg', 'log', '-R', self.config.repository, '-r', 'default',
      '--template', '{rev}', '--config', 'defaults.log=']
    return subprocess.check_output(command)

  def getChanges(self):
    """
      retrieve changes between the current and previous ("first") revision
    """

    command = ['hg', 'log', '-R', self.config.repository, '-r', 'tip:0',
      '-b', 'default', '-l', '50', '--encoding', 'utf-8',
      '--template', '{date|isodate}\\0{author|person}\\0{rev}\\0{desc}\\0\\0',
      '--config', 'defaults.log=']
    result = subprocess.check_output(command).decode('utf-8')

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
    subprocess.check_call(command)

    # Make sure to process the dependencies file if it is present
    import logging
    logging.disable(logging.WARNING)
    try:
      from buildtools.ensure_dependencies import resolve_deps
      resolve_deps(self.tempdir, self_update=False,
          overrideroots={"hg": os.path.dirname(self.config.repository)},
          skipdependencies={"buildtools"})
    finally:
      logging.disable(logging.NOTSET)

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
    template.stream({'changes': changes}).dump(changelogPath, encoding='utf-8')

    linkPath = os.path.join(baseDir, '00latest.changelog.xhtml')
    if hasattr(os, 'symlink'):
      if os.path.exists(linkPath):
        os.remove(linkPath)
      os.symlink(os.path.basename(changelogPath), linkPath)
    else:
      shutil.copyfile(changelogPath, linkPath)

  def readGeckoMetadata(self):
    """
      read Gecko-specific metadata file from a cloned repository
      and parse id, version, basename and the compat section
      out of the file
    """
    import buildtools.packagerGecko as packager
    metadata = packager.readMetadata(self.tempdir, self.config.type)
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

  def readSafariMetadata(self):
    import buildtools.packagerSafari as packager
    metadata = packager.readMetadata(self.tempdir, self.config.type)

    self.certificateID = getSafariCertificateID(self.config.keyFile)
    self.version = packager.getBuildVersion(self.tempdir, metadata, False, self.revision)
    self.shortVersion = metadata.get("general", "version")
    self.basename = metadata.get("general", "basename")

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
    elif self.config.type == 'safari':
      manifestPath = os.path.join(baseDir, "updates.plist")
      templateName = 'safariUpdateManifest'
    elif self.config.type == 'android':
      manifestPath = os.path.join(baseDir, "updates.xml")
      templateName = 'androidUpdateManifest'

      # ABP for Android used to have its own update manifest format. We need to
      # generate both that and the new one in the libadblockplus format as long
      # as a significant amount of users is on an old version.
      newManifestPath = os.path.join(baseDir, "update.json")
      writeAndroidUpdateManifest(newManifestPath, [{
        'basename': self.basename,
        'version': self.version,
        'updateURL': self.updateURL
      }])
    else:
      manifestPath = os.path.join(baseDir, "update.rdf")
      templateName = 'geckoUpdateManifest'

    template = get_template(get_config().get('extensions', templateName))
    template.stream({'extensions': [self]}).dump(manifestPath)

  def writeIEUpdateManifest(self, versions):
    """
      Writes update.json file for the latest IE build
    """
    if len(versions) == 0:
      return

    version = versions[0]
    packageName = self.basename + '-' + version + self.config.packageSuffix
    updateURL = urlparse.urljoin(self.config.nightliesURL, self.basename + '/' + packageName + '?update')
    baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
    manifestPath = os.path.join(baseDir, 'update.json')

    from sitescripts.extensions.utils import writeIEUpdateManifest as doWrite
    doWrite(manifestPath, [{
      'basename': self.basename,
      'version': version,
      'updateURL': updateURL
    }])

    for suffix in (self.config.packageSuffix, self.config.packageSuffix.replace("-x64", "-x86")):
      linkPath = os.path.join(baseDir, '00latest%s' % suffix)
      outputPath = os.path.join(baseDir, self.basename + '-' + version + suffix)
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
    self.path = os.path.join(baseDir, outputFile)
    self.updateURL = urlparse.urljoin(self.config.nightliesURL, self.basename + '/' + outputFile + '?update')

    if self.config.type == 'android':
      apkFile = open(self.path, 'wb')

      try:
        try:
          port = get_config().get('extensions', 'androidBuildPort')
        except ConfigParser.NoOptionError:
          port = '22'
        buildCommand = ['ssh', '-p', port, get_config().get('extensions', 'androidBuildHost')]
        buildCommand.extend(map(pipes.quote, ['/home/android/bin/makedebugbuild.py', '--revision', self.revision, '--version', self.version, '--stdout']))
        subprocess.check_call(buildCommand, stdout=apkFile, close_fds=True)
      except:
        # clear broken output if any
        if os.path.exists(self.path):
          os.remove(self.path)
        raise
    elif self.config.type == 'chrome' or self.config.type == 'opera':
      import buildtools.packagerChrome as packager
      packager.createBuild(self.tempdir, type=self.config.type, outFile=self.path, buildNum=self.revision, keyFile=self.config.keyFile, experimentalAPI=self.config.experimental)
    elif self.config.type == 'safari':
      import buildtools.packagerSafari as packager
      packager.createBuild(self.tempdir, type=self.config.type, outFile=self.path, buildNum=self.revision, keyFile=self.config.keyFile)
    else:
      import buildtools.packagerGecko as packager
      packager.createBuild(self.tempdir, outFile=self.path, buildNum=self.revision, keyFile=self.config.keyFile)

    if not os.path.exists(self.path):
      raise Exception("Build failed, output file hasn't been created")

    linkPath = os.path.join(baseDir, '00latest%s' % self.config.packageSuffix)
    if hasattr(os, 'symlink'):
      if os.path.exists(linkPath):
        os.remove(linkPath)
      os.symlink(os.path.basename(self.path), linkPath)
    else:
      shutil.copyfile(self.path, linkPath)

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
    subprocess.check_call(command)

    try:
      import buildtools.build as build
      outputPath = os.path.join(self.config.docsDirectory, self.basename)
      build.generateDocs(self.tempdir, None, [("-t", docsdir), ("-q", "")], [outputPath], self.config.type)
    finally:
      shutil.rmtree(docsdir, ignore_errors=True)

  def uploadToChromeWebStore(self):
    # Google APIs use HTTP error codes with error message in body. So we add
    # the response body to the HTTPError to get more meaningful error messages.

    class HTTPErrorBodyHandler(urllib2.HTTPDefaultErrorHandler):
      def http_error_default(self, req, fp, code, msg, hdrs):
        raise urllib2.HTTPError(req.get_full_url(), code, '%s\n%s' % (msg, fp.read()), hdrs, fp)

    opener = urllib2.build_opener(HTTPErrorBodyHandler)

    # use refresh token to obtain a valid access token
    # https://developers.google.com/accounts/docs/OAuth2WebServer#refresh

    response = json.load(opener.open(
      'https://accounts.google.com/o/oauth2/token',

      urlencode([
        ('refresh_token', self.config.refreshToken),
        ('client_id', self.config.clientID),
        ('client_secret', self.config.clientSecret),
        ('grant_type', 'refresh_token'),
      ])
    ))

    auth_token = '%s %s' % (response['token_type'], response['access_token'])

    # upload a new version with the Chrome Web Store API
    # https://developer.chrome.com/webstore/using_webstore_api#uploadexisitng

    request = urllib2.Request('https://www.googleapis.com/upload/chromewebstore/v1.1/items/' + self.config.devbuildGalleryID)
    request.get_method = lambda: 'PUT'
    request.add_header('Authorization', auth_token)
    request.add_header('x-goog-api-version', '2')

    with open(self.path, 'rb') as file:
      if file.read(8) != 'Cr24\x02\x00\x00\x00':
        raise Exception('not a chrome extension or unknown CRX version')

      # skip public key and signature
      file.seek(sum(struct.unpack('<II', file.read(8))), os.SEEK_CUR)

      request.add_header('Content-Length', os.fstat(file.fileno()).st_size - file.tell())
      request.add_data(file)

      response = json.load(opener.open(request))

    if response['uploadState'] == 'FAILURE':
      raise Exception(response['itemError'])

    # publish the new version on the Chrome Web Store
    # https://developer.chrome.com/webstore/using_webstore_api#publishpublic

    request = urllib2.Request('https://www.googleapis.com/chromewebstore/v1.1/items/%s/publish' % self.config.devbuildGalleryID)
    request.get_method = lambda: 'POST'
    request.add_header('Authorization', auth_token)
    request.add_header('x-goog-api-version', '2')
    request.add_header('Content-Length', '0')

    response = json.load(opener.open(request))

    if any(status not in ('OK', 'ITEM_PENDING_REVIEW') for status in response['status']):
      raise Exception({'status': response['status'], 'statusDetail': response['statusDetail']})

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
        elif self.config.type == 'safari':
          self.readSafariMetadata()
        else:
          self.readGeckoMetadata()

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

      if self.config.type == 'chrome' and self.config.clientID and self.config.clientSecret and self.config.refreshToken:
        self.uploadToChromeWebStore()
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
