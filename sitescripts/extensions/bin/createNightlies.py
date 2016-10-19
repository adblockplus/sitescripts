# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2016 Eyeo GmbH
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

import ConfigParser
import base64
from datetime import datetime
import hashlib
import hmac
import json
import logging
import os
import pipes
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from urllib import urlencode
import urllib2
import urlparse
from xml.dom.minidom import parse as parseXml

from sitescripts.extensions.utils import (
    compareVersions, Configuration,
    writeAndroidUpdateManifest
)
from sitescripts.utils import get_config, get_template

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
        self.buildNum = None
        self.tempdir = None
        self.outputFilename = None
        self.changelogFilename = None

    def hasChanges(self):
        return self.revision != self.previousRevision

    def getCurrentRevision(self):
        """
            retrieves the current revision ID from the repository
        """
        command = [
            'hg', 'id', '-i', '-r', self.config.revision, '--config',
            'defaults.id=', self.config.repository
        ]
        return subprocess.check_output(command).strip()

    def getCurrentBuild(self):
        """
            calculates the (typically numerical) build ID for the current build
        """
        command = ['hg', 'id', '-n', '--config', 'defaults.id=', self.tempdir]
        build = subprocess.check_output(command).strip()
        if self.config.type == 'gecko':
            build += '-beta'
        return build

    def getChanges(self):
        """
          retrieve changes between the current and previous ("first") revision
        """

        command = [
            'hg', 'log', '-R', self.tempdir, '-r',
            'ancestors({})'.format(self.config.revision), '-l', '50',
            '--encoding', 'utf-8', '--template',
            '{date|isodate}\\0{author|person}\\0{rev}\\0{desc}\\0\\0',
            '--config', 'defaults.log='
        ]
        result = subprocess.check_output(command).decode('utf-8')

        for change in result.split('\x00\x00'):
            if change:
                date, author, revision, description = change.split('\x00')
                yield {'date': date, 'author': author, 'revision': revision, 'description': description}

    def copyRepository(self):
        """
          Create a repository copy in a temporary directory
        """
        self.tempdir = tempfile.mkdtemp(prefix=self.config.repositoryName)
        command = ['hg', 'clone', '-q', self.config.repository,  '-u',
                   self.config.revision, self.tempdir]
        subprocess.check_call(command)

        # Make sure to run ensure_dependencies.py if present
        depscript = os.path.join(self.tempdir, 'ensure_dependencies.py')
        if os.path.isfile(depscript):
            subprocess.check_call([sys.executable, depscript, '-q'])

    def writeChangelog(self, changes):
        """
          write the changelog file into the cloned repository
        """
        baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
        if not os.path.exists(baseDir):
            os.makedirs(baseDir)
        changelogFile = '%s-%s.changelog.xhtml' % (self.basename, self.version)
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
        self.extensionID = metadata.get('general', 'id')
        self.version = packager.getBuildVersion(self.tempdir, metadata, False,
                                                self.buildNum)
        self.basename = metadata.get('general', 'basename')
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
        self.version = root.attributes['android:versionName'].value
        while self.version.count('.') < 2:
            self.version += '.0'
        self.version = '%s.%s' % (self.version, self.buildNum)

        usesSdk = manifest.getElementsByTagName('uses-sdk')[0]
        self.minSdkVersion = usesSdk.attributes['android:minSdkVersion'].value
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
        self.version = packager.getBuildVersion(self.tempdir, metadata, False,
                                                self.buildNum)
        self.basename = metadata.get('general', 'basename')

        self.compat = []
        if metadata.has_section('compat') and metadata.has_option('compat', 'chrome'):
            self.compat.append({'id': 'chrome', 'minVersion': metadata.get('compat', 'chrome')})

    def readSafariMetadata(self):
        import buildtools.packagerSafari as packager
        from buildtools import xarfile
        metadata = packager.readMetadata(self.tempdir, self.config.type)
        certs = xarfile.read_certificates_and_key(self.config.keyFile)[0]

        self.certificateID = packager.get_developer_identifier(certs)
        self.version = packager.getBuildVersion(self.tempdir, metadata, False,
                                                self.buildNum)
        self.shortVersion = metadata.get('general', 'version')
        self.basename = metadata.get('general', 'basename')
        self.updatedFromGallery = False

    def writeUpdateManifest(self):
        """
          Writes update.rdf file for the current build
        """
        baseDir = os.path.join(self.config.nightliesDirectory, self.basename)
        if self.config.type == 'safari':
            manifestPath = os.path.join(baseDir, 'updates.plist')
            templateName = 'safariUpdateManifest'
        elif self.config.type == 'android':
            manifestPath = os.path.join(baseDir, 'updates.xml')
            templateName = 'androidUpdateManifest'
        else:
            return

        if not os.path.exists(baseDir):
            os.makedirs(baseDir)

        # ABP for Android used to have its own update manifest format. We need to
        # generate both that and the new one in the libadblockplus format as long
        # as a significant amount of users is on an old version.
        if self.config.type == 'android':
            newManifestPath = os.path.join(baseDir, 'update.json')
            writeAndroidUpdateManifest(newManifestPath, [{
                'basename': self.basename,
                'version': self.version,
                'updateURL': self.updateURL
            }])

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

        for suffix in ['-x86.msi', '-x64.msi', '-gpo-x86.msi', '-gpo-x64.msi']:
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
        outputFile = '%s-%s%s' % (self.basename, self.version, self.config.packageSuffix)
        self.path = os.path.join(baseDir, outputFile)
        self.updateURL = urlparse.urljoin(self.config.nightliesURL, self.basename + '/' + outputFile + '?update')

        if self.config.type == 'android':
            apkFile = open(self.path, 'wb')

            try:
                try:
                    port = get_config().get('extensions', 'androidBuildPort')
                except ConfigParser.NoOptionError:
                    port = '22'
                command = ['ssh', '-p', port, get_config().get('extensions', 'androidBuildHost')]
                command.extend(map(pipes.quote, [
                    '/home/android/bin/makedebugbuild.py', '--revision',
                    self.buildNum, '--version', self.version, '--stdout'
                ]))
                subprocess.check_call(command, stdout=apkFile, close_fds=True)
            except:
                # clear broken output if any
                if os.path.exists(self.path):
                    os.remove(self.path)
                raise
        else:
            env = os.environ
            spiderMonkeyBinary = self.config.spiderMonkeyBinary
            if spiderMonkeyBinary:
                env = dict(env, SPIDERMONKEY_BINARY=spiderMonkeyBinary)

            command = [os.path.join(self.tempdir, 'build.py'),
                       '-t', self.config.type, 'build', '-b', self.buildNum]
            if self.config.type != 'gecko':
                command.extend(['-k', self.config.keyFile])
            command.append(self.path)
            subprocess.check_call(command, env=env)

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
        versions.sort(compareVersions, reverse=True)
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
        outputFile = 'index.html'
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

    def uploadToMozillaAddons(self):
        import urllib3

        header = {
            'alg': 'HS256',     # HMAC-SHA256
            'typ': 'JWT',
        }

        issued = int(time.time())
        payload = {
            'iss': get_config().get('extensions', 'amo_key'),
            'jti': random.random(),
            'iat': issued,
            'exp': issued + 60,
        }

        input = '{}.{}'.format(
            base64.b64encode(json.dumps(header)),
            base64.b64encode(json.dumps(payload))
        )

        signature = hmac.new(get_config().get('extensions', 'amo_secret'),
                             msg=input,
                             digestmod=hashlib.sha256).digest()
        token = '{}.{}'.format(input, base64.b64encode(signature))

        upload_url = ('https://addons.mozilla.org/api/v3/addons/{}/'
                      'versions/{}/').format(self.extensionID, self.version)

        with open(self.path, 'rb') as file:
            data, content_type = urllib3.filepost.encode_multipart_formdata({
                'upload': (
                    os.path.basename(self.path),
                    file.read(),
                    'application/x-xpinstall'
                )
            })

        request = urllib2.Request(upload_url, data=data)
        request.add_header('Content-Type', content_type)
        request.add_header('Authorization', 'JWT ' + token)
        request.get_method = lambda: 'PUT'

        try:
            urllib2.urlopen(request).close()
        except urllib2.HTTPError as e:
            try:
                logging.error(e.read())
            finally:
                e.close()
            raise

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
                self.buildNum = self.getCurrentBuild()

                # get meta data from the repository
                if self.config.type == 'android':
                    self.readAndroidMetadata()
                elif self.config.type == 'chrome':
                    self.readChromeMetadata()
                elif self.config.type == 'safari':
                    self.readSafariMetadata()
                else:
                    self.readGeckoMetadata()

                # create development build
                self.build()

                # write out changelog
                self.writeChangelog(self.getChanges())

                # write update manifest
                if self.config.type != 'gecko':
                    self.writeUpdateManifest()

            # retire old builds
            versions = self.retireBuilds()

            if self.config.type == 'ie':
                self.writeIEUpdateManifest(versions)

            # update index page
            self.updateIndex(versions)

            # update nightlies config
            self.config.latestRevision = self.revision

            if self.config.type == 'gecko' and self.config.galleryID and get_config().has_option('extensions', 'amo_key'):
                self.uploadToMozillaAddons()
            elif self.config.type == 'chrome' and self.config.clientID and self.config.clientSecret and self.config.refreshToken:
                self.uploadToChromeWebStore()
        finally:
            # clean up
            if self.tempdir:
                shutil.rmtree(self.tempdir, ignore_errors=True)


def main():
    """
      main function for createNightlies.py
    """
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
        except Exception as ex:
            logging.error('The build for %s failed:', repo)
            logging.exception(ex)

    file = open(nightlyConfigFile, 'wb')
    nightlyConfig.write(file)


if __name__ == '__main__':
    main()
