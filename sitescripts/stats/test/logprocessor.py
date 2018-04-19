# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-present eyeo GmbH
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

import unittest
import sitescripts.stats.bin.logprocessor as logprocessor
from datetime import datetime


class Test(unittest.TestCase):
    longMessage = True
    maxDiff = None

    def test_uaparsing(self):
        tests = [
            ('Firefox', '25.0', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20130730 Firefox/25.0'),
            ('Firefox', '25.0', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:28.0) Gecko/20130730 Firefox/25.0'),
            ('Firefox', '25.0', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0.1) Gecko/20130730 Firefox/25.0.1'),
            ('Firefox Mobile', '15.0', 'Mozilla/5.0 (Maemo; Mobile; rv:15.0) Gecko/20120829 Firefox/15.0 Fennec/15.0'),
            ('Firefox Mobile', '14.0', 'Mozilla/5.0 (Android; Mobile; rv:14.0) Gecko/14.0 Firefox/14.0a2'),
            ('Firefox Tablet', '26.0', 'Mozilla/5.0 (Android; Tablet; rv:26.0) Gecko/26.0 Firefox/26.0'),
            ('Thunderbird', '24.0', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:24.0) Gecko/20100101 Thunderbird/24.0a2 Lightning/2.6a2'),
            ('SeaMonkey', '2.19', 'Mozilla/5.0 (Windows NT 5.1; rv:22.0) Gecko/20100101 Firefox/22.0 SeaMonkey/2.19'),
            ('K-Meleon', '1.5', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; ru-RU; rv:1.8.1.24pre) Gecko/20100228 K-Meleon/1.5.4'),
            ('Prism', '1.0', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.20) Gecko/20110803 Prism/1.0b4'),
            ('Gecko', '22.0', 'Mozilla/5.0 (Windows NT 5.1; rv:22.0) Gecko/20100101 FooBar/1.0'),
            ('Opera', '11.10', 'Opera/9.80 (Android; Opera Mini/15.0.1162/30.3558; U; it) Presto/2.8.119 Version/11.10'),
            ('Opera', '9.80', 'Opera/9.80 (Android; Opera Mini/15.0.1162/30.3558; U; it) Presto/2.8.119'),
            ('Opera', '15.0', 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 Safari/537.36 OPR/15.0.1147.148'),
            ('Chrome', '28.0', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 Safari/537.36'),
            ('Chrome', '28.0', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Iron/28.0.1550.0 Chrome/28.0.1550.0 Safari/537.36'),
            ('Safari', '5.0', 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us) AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16'),
            ('Mobile Safari', '4.0', 'Mozilla/5.0 (Linux; U; Android 4.0.4; pt-br; LG-E400 Build/IMM76L; CyanogenMod-9) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'),
            ('CoolNovo', '2.0.9', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36 CoolNovo/2.0.9.11'),
            ('WebKit', '', 'Mozilla/5.0 (Linux; U; Android 4.2.1; zh-CN; P7 Build/JRO03C) AppleWebKit/534.31 (KHTML, like Gecko) UCBrowser/9.2.0.308 U3/0.8.0 Mobile Safari/534.31'),
            ('MSIE', '10.0', 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)'),
            ('MSIE', '7.0', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.3; Trident/7.0; .NET4.0E; .NET4.0C)'),
            ('MSIE', '11.0', 'Mozilla/5.0 (Windows NT 6.3; ARM; Trident/7.0; Touch; rv:11.0) like Gecko'),
            ('Trident', '7.0', 'Mozilla/5.0 (Windows NT 6.3; ARM; Trident/7.0; Touch) like Gecko'),
            ('Edge', '12', 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36 Edge/12.0'),
            ('Edge', '12', 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10136'),
            ('Edge', '12', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/538.36 (KHTML, like Gecko) Edge/12.10240'),
            ('Edge', '12', 'Mozilla/5.0 (Windows NT 6.3; Win64, x64; Touch) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36 Edge/12.0 (Touch; Trident/7.0; .NET4.0E; .NET4.0C; .NET CLR 3.5.30729; .NET CLR 2.0.50727; .NET CLR 3.0.30729; HPNTDFJS; H9P; InfoPath'),
            ('Android', '', 'AndroidDownloadManager'),
            ('Android', '4.1', 'AndroidDownloadManager/4.1.1 (Linux; U; Android 4.1.1; A210 Build/JRO03H)'),
            ('Android', '4.0', 'Dalvik/1.6.0 (Linux; U; Android 4.0.3; KFOT Build/IML74K)'),
            ('Android', '4.3', 'Dalvik/1.6.0 (Linux; U; Android 4.3; Nexus 7 Build/JSS15J)'),
            ('Android', '', 'Apache-HttpClient/UNAVAILABLE (java 1.4)'),
            ('ABP', '', 'Adblock Plus'),
            ('Other', '', '-'),
        ]
        for expected_browser, expected_version, ua in tests:
            self.assertEqual(logprocessor.parse_ua(ua), (expected_browser, expected_version), "Parsing user agent '%s'" % ua)

    def test_ipprocessing(self):
        country = None

        class FakeGeo(object):
            ip_checked = None

            def country_code_by_addr(self, ip):
                self.ip_checked = ip
                return country

        tests = [
            ('1.2.3.4', 'xy', '1.2.3.4', 'v4', 'xy'),
            ('::ffff:1.2.3.4', 'xy', '1.2.3.4', 'v4', 'xy'),
            ('1.2.3.4', '--', '1.2.3.4', 'v4', 'unknown'),
            ('1.2.3.4', '', '1.2.3.4', 'v4', 'unknown'),
            ('::ffff:1.2.3.4', None, '1.2.3.4', 'v4', 'unknown'),
            ('::1', 'xy', '::1', 'v6', 'xy'),
            ('FE80:0000:0000:0000:0202:B3FF:FE1E:8329', None, 'FE80:0000:0000:0000:0202:B3FF:FE1E:8329', 'v6', 'unknown'),
        ]
        for ip, country, expected_ip, expected_type, expected_country in tests:
            fake_geo = FakeGeo()
            fake_geov6 = FakeGeo()
            self.assertEqual(logprocessor.process_ip(ip, fake_geo, fake_geov6), (expected_ip, expected_country), "Processing IP '%s'" % ip)
            if expected_type == 'v4':
                self.assertEqual(fake_geo.ip_checked, expected_ip, "GeoIP check for IP '%s'" % ip)
                self.assertEqual(fake_geov6.ip_checked, None, "GeoIPv6 check for IP '%s'" % ip)
            else:
                self.assertEqual(fake_geo.ip_checked, None, "GeoIP check for IP '%s'" % ip)
                self.assertEqual(fake_geov6.ip_checked, expected_ip, "GeoIPv6 check for IP '%s'" % ip)

    def test_timeparsing(self):
        tests = [
            ('31/Jul/2013:12:03:37', 0, 0, datetime(2013, 07, 31, 12, 03, 37), '201307'),
            ('31/Jul/2013:12:03:37', 5, 0, datetime(2013, 07, 31, 7, 03, 37), '201307'),
            ('31/Jul/2013:12:03:37', -5, 0, datetime(2013, 07, 31, 17, 03, 37), '201307'),
            ('31/Jul/2013:12:03:37', 5, 30, datetime(2013, 07, 31, 6, 33, 37), '201307'),
            ('31/Jul/2013:12:03:37', -5, 30, datetime(2013, 07, 31, 17, 33, 37), '201307'),
        ]
        for timestr, tz_hours, tz_minutes, expected_time, expected_month in tests:
            self.assertEqual(logprocessor.parse_time(timestr, tz_hours, tz_minutes),
                             (expected_time, expected_month, expected_time.day, expected_time.weekday(), expected_time.hour),
                             "Parsing time string '%s %+03i%02i'" % (timestr, tz_hours, tz_minutes))

    def test_pathparsing(self):
        tests = [
            ('/foo.txt', 'foo.txt', ''),
            ('/foo.txt?', 'foo.txt', ''),
            ('/foo.txt?asdf', 'foo.txt', 'asdf'),
            ('http://example.com/foo.txt', 'foo.txt', ''),
            ('/xyz/foo.txt?asdf', 'xyz/foo.txt', 'asdf'),
            ('/xyz/foo+bar.txt?asdf', 'xyz/foo+bar.txt', 'asdf'),
            ('/xyz/foo%2Bbar%2etxt?asdf', 'xyz/foo+bar.txt', 'asdf'),
            ('/xyz/%D1%82%D0%B5%D1%81%D1%82.txt', u'xyz/\u0442\u0435\u0441\u0442.txt', ''),
            ('/xyz/foo%8Cbar.txt?asdf', 'xyz/foo%8Cbar.txt', 'asdf'),
        ]
        for path, expected_file, expected_query in tests:
            self.assertEqual(logprocessor.parse_path(path), (expected_file, expected_query), "Parsing path '%s'" % path)

    def test_downloaderdata(self):
        tests = [
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                '',
                '',
                'unknown/unknown',
                'unknown/unknown',
                'unknown/unknown',
                'unknown',
                'unknown',
                '',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&application=firefox&applicationVersion=22.0a1&platform=gecko&platformVersion=23.0&lastVersion=0',
                '-',
                'adblockplus/2.3.1',
                'firefox/22.0',
                'gecko/23.0',
                'unknown',
                'unknown',
                'firstDownload',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&platform=gecko&platformVersion=23.0&lastVersion=201307311200-1/0',
                '-',
                'adblockplus/2.3.1',
                'unknown/unknown',
                'gecko/23.0',
                '0 hour(s)',
                'same day',
                '',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&platform=gecko&platformVersion=23.0&lastVersion=201307302200-1/3',
                '-',
                'adblockplus/2.3.1',
                'unknown/unknown',
                'gecko/23.0',
                '14 hour(s)',
                '1 day(s)',
                'firstInDay',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&platform=gecko&platformVersion=23.0&lastVersion=201307282200',
                '-',
                'adblockplus/2.3.1',
                'unknown/unknown',
                'gecko/23.0',
                '2 day(s)',
                '3 day(s)',
                'firstInWeek firstInDay',
            ),
            (
                datetime(2013, 8, 2, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&platform=gecko&platformVersion=23.0&lastVersion=201307311200',
                '-',
                'adblockplus/2.3.1',
                'unknown/unknown',
                'gecko/23.0',
                '2 day(s)',
                '2 day(s)',
                'firstInMonth firstInDay',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&platform=gecko&platformVersion=23.0&lastVersion=201306302200',
                '-',
                'adblockplus/2.3.1',
                'unknown/unknown',
                'gecko/23.0',
                '1 month(s)',
                '1 month(s)',
                'firstInMonth firstInWeek firstInDay',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&platform=gecko&platformVersion=23.0&lastVersion=201305302200',
                '-',
                'adblockplus/2.3.1',
                'unknown/unknown',
                'gecko/23.0',
                '2 month(s)',
                '2 month(s)',
                'firstInMonth firstInWeek firstInDay',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockplus&addonVersion=2.3.1&platform=gecko&platformVersion=23.0.1&lastVersion=201206302200',
                '-',
                'adblockplus/2.3.1',
                'unknown/unknown',
                'gecko/23.0',
                '1 year(s)',
                '1 year(s)',
                'firstInMonth firstInWeek firstInDay',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                'addonName=adblockedge&addonVersion=2.1.2&platform=gecko&platformVersion=23.0.1&lastVersion=201206302200',
                '-',
                'adblockedge/2.1.2',
                'unknown/unknown',
                'gecko/23.0',
                '1 year(s)',
                'unknown',
                'firstInMonth firstInWeek firstInDay',
            ),
            (
                datetime(2013, 07, 31, 12, 03, 00),
                'easylist.txt',
                '_=1375142394357',
                'AdBlock/2.5.4',
                'chromeadblock/2.5.4',
                'unknown/unknown',
                'unknown/unknown',
                'unknown',
                'unknown',
                '',
            ),
        ]
        for time, file, query, clientid, expected_addon, expected_application, expected_platform, expected_interval, expected_previous, expected_flags in tests:
            info = {'time': time, 'file': file, 'query': query, 'clientid': clientid}
            logprocessor.parse_downloader_query(info)
            self.assertEqual('%s/%s' % (info['addonName'], info['addonVersion']), expected_addon, "Add-on for query '%s'" % query)
            self.assertEqual('%s/%s' % (info['application'], info['applicationVersion']), expected_application, "Application for query '%s'" % query)
            self.assertEqual('%s/%s' % (info['platform'], info['platformVersion']), expected_platform, "Platform for query '%s'" % query)
            self.assertEqual(info['downloadInterval'], expected_interval, "Download interval for query '%s'" % query)
            self.assertEqual(info['previousDownload'], expected_previous, "Previous download for query '%s'" % query)

            flags = []
            for flag in ('firstDownload', 'firstInMonth', 'firstInWeek', 'firstInDay'):
                if flag in info:
                    flags.append(flag)
            self.assertEqual(' '.join(flags), expected_flags, "Flags for query '%s'" % query)

    def test_nameparsing(self):
        tests = [
            ('devbuilds/adblockplus/update.rdf', 'adblockplus'),
            ('adblockpluschrome-experimental/updates.xml', 'adblockpluschrome-experimental'),
            ('update.json', None),
        ]
        for file, expected_name in tests:
            self.assertEqual(logprocessor.parse_addon_name(file), expected_name, "Getting add-on name for file '%s'" % file)

    def test_geckoqueryparsing(self):
        tests = [
            (
                'reqVersion=2&id={d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}&version=2.3.1.3707&maxAppVersion=25.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=22.0&appOS=Darwin&appABI=x86_64-gcc3&locale=en-US&currentAppVersion=22.0&updateType=112',
                '2.3.1.3707', 'firefox', '22.0',
            ),
            (
                'reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97',
                '1.0.4a.74', 'firefox', '25.0',
            ),
            (
                'reqVersion=2&id={d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}&version=1.3a.20100925&maxAppVersion=2.1b1&status=userEnabled,incompatible&appID={92650c4d-4b8e-4d2a-b7eb-24ecf4f6b63a}&appVersion=2.19&appOS=WINNT&appABI=x86-msvc&locale=en-US&currentAppVersion=2.19&updateType=112',
                '1.3a.20100925', 'seamonkey', '2.19',
            ),
        ]
        for query, expected_version, expected_application, expected_applicationversion in tests:
            self.assertEqual(logprocessor.parse_gecko_query(query), (expected_version, expected_application, expected_applicationversion), "Parsing Gecko query '%s'" % query)

    def test_chromequeryparsing(self):
        tests = [
            (
                'os=win&arch=x86&nacl_arch=x86-64&prod=chromecrx&prodchannel=stable&prodversion=28.0.1500.72&x=id%3Dldcecbkkoecffmfljeihcmifjjdoepkn%26v%3D1.5.3.977%26uc',
                '1.5.3.977', 'chrome', '28.0',
            ),
            (
                'x=id%3Dldcecbkkoecffmfljeihcmifjjdoepkn%26v%3D1.5.3.977%26uc',
                '1.5.3.977', 'unknown', 'unknown',
            ),
            (
                'api=15&build=256&locale=ru_ru&device=LGE%20LG-P990',
                'unknown', 'unknown', 'unknown',
            ),
        ]
        for query, expected_version, expected_application, expected_applicationversion in tests:
            self.assertEqual(logprocessor.parse_chrome_query(query), (expected_version, expected_application, expected_applicationversion), "Parsing Chrome query '%s'" % query)

    def test_updateflagparsing(self):
        tests = [
            ('update', 'update'),
            ('', 'install'),
            ('foo', 'install'),
            ('update&foo', 'install'),
        ]
        for query, expected_result in tests:
            self.assertEqual(logprocessor.parse_update_flag(query), expected_result, "Checking update flag for query '%s'" % query)

    def test_recordparsing(self):
        class FakeGeo(object):
            def country_code_by_addr(self, ip):
                return 'xy'

        tests = [
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/adblockpluschrome/updates.xml?os=mac&arch=x86&nacl_arch=x86-32&prod=chromecrx&prodchannel=stable&prodversion=28.0.1500.71&x=id%3Dldcecbkkoecffmfljeihcmifjjdoepkn%26v%3D1.5.3.977%26uc HTTP/1.1" 200 867 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.71 Safari/537.36" "-" https" "en-US" "downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'devbuilds/adblockpluschrome/updates.xml',
                    'query': 'os=mac&arch=x86&nacl_arch=x86-32&prod=chromecrx&prodchannel=stable&prodversion=28.0.1500.71&x=id%3Dldcecbkkoecffmfljeihcmifjjdoepkn%26v%3D1.5.3.977%26uc',
                    'size': 867,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Chrome',
                    'uaversion': '28.0',
                    'fullua': 'Chrome 28.0',
                    'clientid': '-',
                    'addonName': 'adblockpluschrome',
                    'addonVersion': '1.5.3.977',
                    'fullAddon': 'adblockpluschrome 1.5.3.977',
                    'application': 'chrome',
                    'applicationVersion': '28.0',
                    'fullApplication': 'chrome 28.0',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/abpcustomization/update.rdf?reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97 HTTP/1.1" 404 867 "-" "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20130730 Firefox/25.0" "-" https" "en-US" "downloads.adblockplus.org" "-"',
                None,
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/abpcustomization/update.rdf?reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97 HTTP/1.1" 301 867 "-" "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20130730 Firefox/25.0" "-" https" "en-US" "downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'devbuilds/abpcustomization/update.rdf',
                    'query': 'reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97',
                    'size': 867,
                    'referrer': '-',
                    'status': 301,
                    'ua': 'Firefox',
                    'uaversion': '25.0',
                    'fullua': 'Firefox 25.0',
                    'clientid': '-',
                    'addonName': 'abpcustomization',
                    'addonVersion': '1.0.4a.74',
                    'fullAddon': 'abpcustomization 1.0.4a.74',
                    'application': 'firefox',
                    'applicationVersion': '25.0',
                    'fullApplication': 'firefox 25.0',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/abpcustomization/update.rdf?reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97 HTTP/1.1" 302 867 "-" "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20130730 Firefox/25.0" "-" https" "en-US" "downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'devbuilds/abpcustomization/update.rdf',
                    'query': 'reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97',
                    'size': 867,
                    'referrer': '-',
                    'status': 302,
                    'ua': 'Firefox',
                    'uaversion': '25.0',
                    'fullua': 'Firefox 25.0',
                    'clientid': '-',
                    'addonName': 'abpcustomization',
                    'addonVersion': '1.0.4a.74',
                    'fullAddon': 'abpcustomization 1.0.4a.74',
                    'application': 'firefox',
                    'applicationVersion': '25.0',
                    'fullApplication': 'firefox 25.0',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/abpcustomization/update.unknown?reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97 HTTP/1.1" 200 867 "-" "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20130730 Firefox/25.0" "-" https" "en-US" "downloads.adblockplus.org" "-"',
                None,
            ),
            (
                '1.2.3.4 corrupted',
                None,
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/abpcustomization/update.rdf?reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97 HTTP/1.1" 200 867 "-" "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20130730 Firefox/25.0" "-" https" "en-US" "downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'devbuilds/abpcustomization/update.rdf',
                    'query': 'reqVersion=2&id=customization@adblockplus.org&version=1.0.4a.74&maxAppVersion=26.0&status=userEnabled&appID={ec8030f7-c20a-464f-9b0e-13a3a9e97384}&appVersion=25.0a1&appOS=WINNT&appABI=x86_64-msvc&locale=en-US&currentAppVersion=25.0a1&updateType=97',
                    'size': 867,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Firefox',
                    'uaversion': '25.0',
                    'fullua': 'Firefox 25.0',
                    'clientid': '-',
                    'addonName': 'abpcustomization',
                    'addonVersion': '1.0.4a.74',
                    'fullAddon': 'abpcustomization 1.0.4a.74',
                    'application': 'firefox',
                    'applicationVersion': '25.0',
                    'fullApplication': 'firefox 25.0',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/adblockplusie/update.json?addonName=adblockplusie&addonVersion=2.0&application=msie64&applicationVersion=10.0&platform=libadblockplus&platformVersion=1.0&lastVersion=0 HTTP/1.1" 200 867 "-" "Adblock Plus" "-" https" "en-US" "downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'devbuilds/adblockplusie/update.json',
                    'query': 'addonName=adblockplusie&addonVersion=2.0&application=msie64&applicationVersion=10.0&platform=libadblockplus&platformVersion=1.0&lastVersion=0',
                    'size': 867,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'ABP',
                    'uaversion': '',
                    'fullua': 'ABP ',
                    'clientid': '-',
                    'addonName': 'adblockplusie',
                    'addonVersion': '2.0',
                    'fullAddon': 'adblockplusie 2.0',
                    'application': 'msie64',
                    'applicationVersion': '10.0',
                    'fullApplication': 'msie64 10.0',
                    'platform': 'libadblockplus',
                    'platformVersion': '1.0',
                    'fullPlatform': 'libadblockplus 1.0',
                    'downloadInterval': 'unknown',
                    'previousDownload': 'unknown',
                    'firstDownload': True,
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /adblockplusandroid-1.1.2.apk HTTP/1.1" 200 49152 "https://adblockplus.org/en/android-install" "Mozilla/5.0 (Linux; U; Android 4.1.2; es-es; GT-I9100 Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30" "-" https "en-US" "downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'adblockplusandroid-1.1.2.apk',
                    'query': '',
                    'size': 49152,
                    'referrer': 'https://adblockplus.org/en/android-install',
                    'status': 200,
                    'ua': 'Mobile Safari',
                    'uaversion': '4.0',
                    'fullua': 'Mobile Safari 4.0',
                    'clientid': '-',
                    'installType': 'install',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /devbuilds/adblockplus/adblockplus-2.3.2.3712.xpi?update HTTP/1.1" 200 827261 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:22.0) Gecko/20100101 Firefox/22.0" "-" https',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'devbuilds/adblockplus/adblockplus-2.3.2.3712.xpi',
                    'query': 'update',
                    'size': 827261,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Firefox',
                    'uaversion': '22.0',
                    'fullua': 'Firefox 22.0',
                    'clientid': None,
                    'installType': 'update',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /exceptionrules.txt?addonName=adblockplus&addonVersion=2.3.2&application=firefox&applicationVersion=22.0&platform=gecko&platformVersion=22.0&lastVersion=201307311503 HTTP/1.1" 200 14303 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:22.0) Gecko/20100101 Firefox/22.0" "-" https "en-US,en;q=0.5" "easylist-downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'exceptionrules.txt',
                    'query': 'addonName=adblockplus&addonVersion=2.3.2&application=firefox&applicationVersion=22.0&platform=gecko&platformVersion=22.0&lastVersion=201307311503',
                    'size': 14303,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Firefox',
                    'uaversion': '22.0',
                    'fullua': 'Firefox 22.0',
                    'clientid': '-',
                    'addonName': 'adblockplus',
                    'addonVersion': '2.3.2',
                    'fullAddon': 'adblockplus 2.3.2',
                    'application': 'firefox',
                    'applicationVersion': '22.0',
                    'fullApplication': 'firefox 22.0',
                    'platform': 'gecko',
                    'platformVersion': '22.0',
                    'fullPlatform': 'gecko 22.0',
                    'downloadInterval': '2 hour(s)',
                    'previousDownload': 'same day',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /easylist.txt?_=1375446528229 HTTP/1.1" 200 326120 "-" "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 Safari/537.36" "-" https "nl-NL,nl;q=0.8,en-US;q=0.6,en;q=0.4" "easylist-downloads.adblockplus.org" "AdBlock/2.6.2"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'easylist.txt',
                    'query': '_=1375446528229',
                    'size': 326120,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Chrome',
                    'uaversion': '28.0',
                    'fullua': 'Chrome 28.0',
                    'clientid': 'AdBlock/2.6.2',
                    'addonName': 'chromeadblock',
                    'addonVersion': '2.6.2',
                    'fullAddon': 'chromeadblock 2.6.2',
                    'application': 'unknown',
                    'applicationVersion': 'unknown',
                    'fullApplication': 'unknown unknown',
                    'platform': 'unknown',
                    'platformVersion': 'unknown',
                    'fullPlatform': 'unknown unknown',
                    'downloadInterval': 'unknown',
                    'previousDownload': 'unknown',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /easylistitaly.txt HTTP/1.1" 200 85879 "-" "-" "-" https "-" "easylist-downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'easylistitaly.txt',
                    'query': '',
                    'size': 85879,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Other',
                    'uaversion': '',
                    'fullua': 'Other ',
                    'clientid': '-',
                    'addonName': 'unknown',
                    'addonVersion': 'unknown',
                    'fullAddon': 'unknown unknown',
                    'application': 'unknown',
                    'applicationVersion': 'unknown',
                    'fullApplication': 'unknown unknown',
                    'platform': 'unknown',
                    'platformVersion': 'unknown',
                    'fullPlatform': 'unknown unknown',
                    'downloadInterval': 'unknown',
                    'previousDownload': 'unknown',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /easylistitaly.tpl HTTP/1.1" 200 85879 "-" "-" "-" https "-" "easylist-downloads.adblockplus.org" "-"',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'easylistitaly.tpl',
                    'query': '',
                    'size': 85879,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Other',
                    'uaversion': '',
                    'fullua': 'Other ',
                    'clientid': '-',
                },
            ),
            (
                '1.2.3.4 - - [31/Jul/2013:12:03:08 -0530] "GET /notification.json?addonName=adblockpluschrome&addonVersion=1.5.3&application=chrome&applicationVersion=28.0.1500.72&platform=chromium&platformVersion=28.0.1500.72&lastVersion=201307292310 HTTP/1.1" 200 299 "-" "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 Safari/537.36" "-" https',
                {
                    'ip': '1.2.3.4',
                    'country': 'xy',
                    'time': datetime(2013, 7, 31, 17, 33, 8),
                    'day': 31,
                    'weekday': 2,
                    'hour': 17,
                    'month': '201307',
                    'file': 'notification.json',
                    'query': 'addonName=adblockpluschrome&addonVersion=1.5.3&application=chrome&applicationVersion=28.0.1500.72&platform=chromium&platformVersion=28.0.1500.72&lastVersion=201307292310',
                    'size': 299,
                    'referrer': '-',
                    'status': 200,
                    'ua': 'Chrome',
                    'uaversion': '28.0',
                    'fullua': 'Chrome 28.0',
                    'clientid': None,
                    'addonName': 'adblockpluschrome',
                    'addonVersion': '1.5.3',
                    'fullAddon': 'adblockpluschrome 1.5.3',
                    'application': 'chrome',
                    'applicationVersion': '28.0',
                    'fullApplication': 'chrome 28.0',
                    'platform': 'chromium',
                    'platformVersion': '28.0',
                    'fullPlatform': 'chromium 28.0',
                    'downloadInterval': '1 day(s)',
                    'previousDownload': '2 day(s)',
                    'firstInDay': True,
                },
            ),
        ]
        for line, expected_record in tests:
            self.assertEqual(logprocessor.parse_record(line, set(), FakeGeo(), FakeGeo()), expected_record, "Parsing log line '%s'" % line)

    def test_record_adding(self):
        tests = [
            (
                {'size': 200},
                {},
                (),
                {'hits': 1, 'bandwidth': 200},
            ),
            (
                {'size': 200},
                {'hits': 12, 'bandwidth': 30},
                (),
                {'hits': 13, 'bandwidth': 230},
            ),
            (
                {'size': 200, 'ua': 'Foo'},
                {'hits': 12, 'bandwidth': 30},
                (),
                {'hits': 13, 'bandwidth': 230, 'ua': {'Foo': {'hits': 1, 'bandwidth': 200}}},
            ),
            (
                {'size': 200, 'ua': 'Foo'},
                {'hits': 12, 'bandwidth': 30, 'ua': {'Bar': {'hits': 21, 'bandwidth': 1200}}},
                (),
                {'hits': 13, 'bandwidth': 230, 'ua': {'Bar': {'hits': 21, 'bandwidth': 1200}, 'Foo': {'hits': 1, 'bandwidth': 200}}},
            ),
            (
                {'size': 200, 'ua': 'Foo', 'bar': 'xyz'},
                {'hits': 12, 'bandwidth': 30, 'ua': {'Foo': {'hits': 21, 'bandwidth': 1200}}},
                (),
                {'hits': 13, 'bandwidth': 230, 'ua': {'Foo': {'hits': 22, 'bandwidth': 1400}}},
            ),
            (
                {'size': 200, 'ua': 'Foo', 'addonName': 'bar'},
                {},
                (),
                {
                    'hits': 1, 'bandwidth': 200,
                    'ua': {'Foo': {'hits': 1, 'bandwidth': 200, 'addonName': {'bar': {'hits': 1, 'bandwidth': 200}}}},
                    'addonName': {'bar': {'hits': 1, 'bandwidth': 200, 'ua': {'Foo': {'hits': 1, 'bandwidth': 200}}}},
                },
            ),
            (
                {'size': 200, 'ua': 'Foo', 'addonName': 'bar', 'platform': 'xyz'},
                {},
                ('platform',),
                {
                    'hits': 1, 'bandwidth': 200,
                    'ua': {'Foo': {'hits': 1, 'bandwidth': 200}},
                    'addonName': {'bar': {'hits': 1, 'bandwidth': 200}},
                },
            ),
        ]
        for info, section, ignored_fields, expected_result in tests:
            logprocessor.add_record(info, section, ignored_fields)
            self.assertEqual(section, expected_result)


if __name__ == '__main__':
    unittest.main()
