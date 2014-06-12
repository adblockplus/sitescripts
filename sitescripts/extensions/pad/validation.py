# This file is part of the Adblock Plus web scripts,
# Copyright (C) 2006-2014 Eyeo GmbH
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

import itertools
import warnings
import re
import urllib2
from xml.dom import minidom
from sitescripts.extensions.pad.language import get_pad_languages

FIELDS = [
  (['XML_DIZ_INFO', 'MASTER_PAD_VERSION_INFO', 'MASTER_PAD_VERSION'], r'^4\.0\Z'),
  (['XML_DIZ_INFO', 'MASTER_PAD_VERSION_INFO', 'MASTER_PAD_EDITOR'], r'^[^<\x09]{0,100}\Z'),
  (['XML_DIZ_INFO', 'MASTER_PAD_VERSION_INFO', 'MASTER_PAD_INFO'], r'^[^<\x09]{0,1000}\Z'),
  (['XML_DIZ_INFO', 'MASTER_PAD_VERSION_INFO', 'CERTIFIED'], r'^[YyNn]\Z'),
  (['XML_DIZ_INFO', 'MASTER_PAD_VERSION_INFO', 'CERTIFICATE_ID'], r'^(crt\-[0-9A-Z]{12}|)\Z'),
  (['XML_DIZ_INFO', 'MASTER_PAD_VERSION_INFO', 'CERTIFICATE_LICENSE'], r'^(http\:\/\/repository\.appvisor\.com\/crt\-[0-9a-z]{12}|)\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'PublisherID'], r'^(pid-[0-9a-z]{12}|)\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Company_Name'], r'^[^<\x09]{2,40}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Address_1'], r'^[a-zA-Z0-9\xbc-\xff .\-,#\/\x27]{0,40}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Address_2'], r'^[a-zA-Z\xbc-\xff0-9 .\-,#\/\x27]{0,40}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'City_Town'], r'^[a-zA-Z\xbc-\xff0-9 .\-,#\/\x27]{2,40}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'State_Province'], r'^[a-zA-Z\xbc-\xff0-9 .\-,\/]{0,30}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Zip_Postal_Code'], r'^[^<\x09]{0,20}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Country'], r'^[a-z A-Z\xbc-\xff\x27-]{2,40}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Company_WebSite_URL'], r'^(http|https):\/\/.{2,120}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Contact_Info', 'Author_First_Name'], r'^[^<\x09]{2,30}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Contact_Info', 'Author_Last_Name'], r'^[^<\x09]{2,30}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Contact_Info', 'Author_Email'], r'^.{2,30}\@.{2,63}\..{2,20}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Contact_Info', 'Contact_First_Name'], r'^[^<\x09]{2,30}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Contact_Info', 'Contact_Last_Name'], r'^[^<\x09]{2,30}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Contact_Info', 'Contact_Email'], r'^.{2,30}\@.{2,63}\..{2,20}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Support_Info', 'Sales_Email'], r'^.{2,30}\@.{2,63}\..{2,20}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Support_Info', 'Support_Email'], r'^.{2,30}\@.{2,63}\..{2,20}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Support_Info', 'General_Email'], r'^.{2,30}\@.{2,63}\..{2,20}\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Support_Info', 'Sales_Phone'], r'^\+{0,2}(([0-9#*()-\/_] *){7,40})?\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Support_Info', 'Support_Phone'], r'^\+{0,2}(([0-9#*()-\/_] *){7,40})?\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Support_Info', 'General_Phone'], r'^\+{0,2}(([0-9#*()-\/_] *){7,40})?\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'Support_Info', 'Fax_Phone'], r'^\+{0,2}(([0-9#*()-\/_] *){7,40})?\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'GooglePlusPage'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'LinkedinPage'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'TwitterCompanyPage'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'FacebookCompanyPage'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Company_Info', 'CompanyStorePage'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'AppID'], r'^(app-[0-9a-z]{12}|)\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Name'], r'^[^<\x09]{1,40}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Version'], r'^[a-zA-Z0-9_.\-]{1,15}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Release_Month'], r'^(0[1-9]|1[0-2])\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Release_Day'], r'^(0[1-9]|[12][0-9]|3[01])\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Release_Year'], r'^(19|20|21)[0-9]{2}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Cost_Dollars'], r'^([0-9]+(\.[0-9]{2})?)?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Cost_Other_Code'], r'^(AED|AFN|ALL|AMD|ANG|AOA|ARS|AUD|AWG|AZM|BAM|BBD|BDT|BGN|BHD|BIF|BMD|BND|BOB|BRL|BSD|BTN|BWP|BYR|BZD|CAD|CDF|CHF|CLP|CNY|COP|COU|CRC|CSD|CZK|CUP|CVE|CYP|DJF|DKK|DOP|DZD|EEK|EGP|ERN|ETB|EUR|FJD|FKP|GBP|GEL|GHC|GIP|GMD|GNF|GTQ|GYD|HKD|HNL|HRK|HTG|HUF|IDR|ILS|INR|IQD|IRR|ISK|JMD|JOD|JPY|KES|KGS|KHR|KMF|KPW|KRW|KWD|KYD|KZT|LAK|LBP|LKR|LRD|LSL|LTL|LVL|LYD|MAD|MDL|MGA|MKD|MMK|MNT|MOP|MRO|MTL|MUR|MVR|MWK|MXN|MYR|MZN|NAD|NGN|NIO|NOK|NPR|NZD|OMR|PAB|PEN|PGK|PHP|PKR|PLN|PYG|QAR|RON|RUB|RWF|SAR|SBD|SCR|SDD|SEK|SGD|SHP|SIT|SKK|SLL|SOS|SRD|STD|SYP|SZL|THB|TJS|TMM|TND|TOP|TRY|TTD|TWD|TZS|UAH|UGX|USD|UYU|UZS|VEB|VND|VUV|WST|XAF|XCD|XOF|XPF|YER|ZAR|ZMK|ZWD)?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Cost_Other'], r'^([0-9]+(\.[0-9]{2})?)?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Type'], r'^(Shareware|Freeware|Adware|Demo|Commercial|Data Only)\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Release_Status'], r'^(Major Update|Minor Update|New Release|Beta|Alpha|Media Only)\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Install_Support'], r'^(Install and Uninstall|Install Only|No Install Support|Uninstall Only)\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_OS_Support'], r'^((Android|BlackBerry|Handheld\/Mobile Other|iPhone|iPad|iPod|iTouch|Java|Linux|Linux Console|Linux Gnome|Linux GPL|Linux Open Source|Mac OS X|Mac Other|MS-DOS|Netware|OpenVMS|Palm|Pocket PC|Symbian|Unix|Win2000|Win7 x32|Win7 x64|Win98|WinMobile|WinOther|WinServer|WinVista|WinVista x64|WinXP|Windows 8|Windows Phone 7|Windows Phone 8|Windows RT|Other|Not Applicable)[, ]*)+\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Language'], r'^(%s|Other|,)+\Z' % '|'.join(get_pad_languages())),
  (['XML_DIZ_INFO', 'Program_Info', 'File_Info', 'File_Size_Bytes'], r'^[0-9]{3,16}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'File_Info', 'File_Size_K'], r'^[0-9.]{1,12}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'File_Info', 'File_Size_MB'], r'^[0-9.]{1,8}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Expire_Info', 'Has_Expire_Info'], r'^[YyNn]\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Expire_Info', 'Expire_Count'], r'^[0-9]{0,15}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Expire_Info', 'Expire_Based_On'], r'^(Days|Uses|Either\/Or)?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Expire_Info', 'Expire_Other_Info'], r'^[^<\x09]{0,100}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Expire_Info', 'Expire_Month'], r'^(0[1-9]|1[0-2])?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Expire_Info', 'Expire_Day'], r'^(0[1-9]|[12][0-9]|3[01])?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Expire_Info', 'Expire_Year'], r'^((19|20|21)[0-9]{2})?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Change_Info'], r'^[^<\x09]{0,300}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Category_Class'], r'^(Audio &amp; Multimedia::Audio Encoders\/Decoders|Audio &amp; Multimedia::Audio File Players|Audio &amp; Multimedia::Audio File Recorders|Audio &amp; Multimedia::CD Burners|Audio &amp; Multimedia::CD Players|Audio &amp; Multimedia::Multimedia Creation Tools|Audio &amp; Multimedia::Music Composers|Audio &amp; Multimedia::Other|Audio &amp; Multimedia::Presentation Tools|Audio &amp; Multimedia::Rippers &amp; Converters|Audio &amp; Multimedia::Speech|Audio &amp; Multimedia::Video Tools|Business::Accounting &amp; Finance|Business::Calculators &amp; Converters|Business::Databases &amp; Tools|Business::Helpdesk &amp; Remote PC|Business::Inventory &amp; Barcoding|Business::Investment Tools|Business::Math &amp; Scientific Tools|Business::Office Suites &amp; Tools|Business::Other|Business::PIMS &amp; Calendars|Business::Project Management|Business::Vertical Market Apps|Communications::Chat &amp; Instant Messaging|Communications::Dial Up &amp; Connection Tools|Communications::E-Mail Clients|Communications::E-Mail List Management|Communications::Fax Tools|Communications::Newsgroup Clients|Communications::Other Comms Tools|Communications::Other E-Mail Tools|Communications::Pager Tools|Communications::Telephony|Communications::Web\/Video Cams|Desktop::Clocks &amp; Alarms|Desktop::Cursors &amp; Fonts|Desktop::Icons|Desktop::Other|Desktop::Screen Savers: Art|Desktop::Screen Savers: Cartoons|Desktop::Screen Savers: Nature|Desktop::Screen Savers: Other|Desktop::Screen Savers: People|Desktop::Screen Savers: Science|Desktop::Screen Savers: Seasonal|Desktop::Screen Savers: Vehicles|Desktop::Themes &amp; Wallpaper|Development::Active X|Development::Basic, VB, VB DotNet|Development::C \/ C\+\+ \/ C\#|Development::Compilers &amp; Interpreters|Development::Components &amp; Libraries|Development::Debugging|Development::Delphi|Development::Help Tools|Development::Install &amp; Setup|Development::Management &amp; Distribution|Development::Other|Development::Source Editors|Education::Computer|Education::Dictionaries|Education::Geography|Education::Kids|Education::Languages|Education::Mathematics|Education::Other|Education::Reference Tools|Education::Science|Education::Teaching &amp; Training Tools|Games &amp; Entertainment::Action|Games &amp; Entertainment::Adventure &amp; Roleplay|Games &amp; Entertainment::Arcade|Games &amp; Entertainment::Board|Games &amp; Entertainment::Card|Games &amp; Entertainment::Casino &amp; Gambling|Games &amp; Entertainment::Kids|Games &amp; Entertainment::Online Gaming|Games &amp; Entertainment::Other|Games &amp; Entertainment::Puzzle &amp; Word Games|Games &amp; Entertainment::Simulation|Games &amp; Entertainment::Sports|Games &amp; Entertainment::Strategy &amp; War Games|Games &amp; Entertainment::Tools &amp; Editors|Graphic Apps::Animation Tools|Graphic Apps::CAD|Graphic Apps::Converters &amp; Optimizers|Graphic Apps::Editors|Graphic Apps::Font Tools|Graphic Apps::Gallery &amp; Cataloging Tools|Graphic Apps::Icon Tools|Graphic Apps::Other|Graphic Apps::Screen Capture|Graphic Apps::Viewers|Home &amp; Hobby::Astrology\/Biorhythms\/Mystic|Home &amp; Hobby::Astronomy|Home &amp; Hobby::Cataloging|Home &amp; Hobby::Food &amp; Drink|Home &amp; Hobby::Genealogy|Home &amp; Hobby::Health &amp; Nutrition|Home &amp; Hobby::Other|Home &amp; Hobby::Personal Finance|Home &amp; Hobby::Personal Interest|Home &amp; Hobby::Recreation|Home &amp; Hobby::Religion|Network &amp; Internet::Ad Blockers|Network &amp; Internet::Browser Tools|Network &amp; Internet::Browsers|Network &amp; Internet::Download Managers|Network &amp; Internet::File Sharing\/Peer to Peer|Network &amp; Internet::FTP Clients|Network &amp; Internet::Network Monitoring|Network &amp; Internet::Other|Network &amp; Internet::Remote Computing|Network &amp; Internet::Search\/Lookup Tools|Network &amp; Internet::Terminal &amp; Telnet Clients|Network &amp; Internet::Timers &amp; Time Synch|Network &amp; Internet::Trace &amp; Ping Tools|Security &amp; Privacy::Access Control|Security &amp; Privacy::Anti-Spam &amp; Anti-Spy Tools|Security &amp; Privacy::Anti-Virus Tools|Security &amp; Privacy::Covert Surveillance|Security &amp; Privacy::Encryption Tools|Security &amp; Privacy::Other|Security &amp; Privacy::Password Managers|Servers::Firewall &amp; Proxy Servers|Servers::FTP Servers|Servers::Mail Servers|Servers::News Servers|Servers::Other Server Applications|Servers::Telnet Servers|Servers::Web Servers|System Utilities::Automation Tools|System Utilities::Backup &amp; Restore|System Utilities::Benchmarking|System Utilities::Clipboard Tools|System Utilities::File &amp; Disk Management|System Utilities::File Compression|System Utilities::Launchers &amp; Task Managers|System Utilities::Other|System Utilities::Printer|System Utilities::Registry Tools|System Utilities::Shell Tools|System Utilities::System Maintenance|System Utilities::Text\/Document Editors|Web Development::ASP &amp; PHP|Web Development::E-Commerce|Web Development::Flash Tools|Web Development::HTML Tools|Web Development::Java &amp; JavaScript|Web Development::Log Analysers|Web Development::Other|Web Development::Site Administration|Web Development::Wizards &amp; Components|Web Development::XML\/CSS Tools)\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_Specific_Category'], r'^(Audio|Business|Development Tools|Education|Games|Graphics|Home\/Hobby|Internet|Miscellaneous|Screen Savers|Utilities)?\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'Program_System_Requirements'], r'^[^<\x09]{0,100}\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'FacebookProductPage'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Program_Info', 'GooglePlusProductPage'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Application_URLs', 'Application_Info_URL'], r'^(http|https):\/\/.{2,120}\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Application_URLs', 'Application_Order_URL'], r'^((http|https):\/\/.{2,120})?\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Application_URLs', 'Application_Screenshot_URL'], r'^(http|https):\/\/.{2,120}\.(gif|jpg|png)\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Application_URLs', 'Application_Icon_URL'], r'^(http|https):\/\/.{2,120}\.(gif|jpg|png)\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Application_URLs', 'Application_XML_File_URL'], r'^(http|https):\/\/.{2,120}\.(xml|cgi|php|asp)\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Application_URLs', 'Video_Link_1_URL'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Application_URLs', 'Video_Link_2_URL'], r'^((http|https):\/\/.{4,120}|)\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Download_URLs', 'Primary_Download_URL'], r'^(http|https|ftp):\/\/.{2,120}\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Download_URLs', 'Secondary_Download_URL'], r'^((http|https|ftp):\/\/.{2,120})?\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Download_URLs', 'Additional_Download_URL_1'], r'^((http|https|ftp):\/\/.{2,120})?\Z'),
  (['XML_DIZ_INFO', 'Web_Info', 'Download_URLs', 'Additional_Download_URL_2'], r'^((http|https|ftp):\/\/.{2,120})?\Z'),
  (['XML_DIZ_INFO', 'Permissions', 'Distribution_Permissions'], r'^[^<]{0,2000}\Z'),
  (['XML_DIZ_INFO', 'Permissions', 'EULA'], r'^[^<]{0,20000}\Z'),
  (['XML_DIZ_INFO', 'Press_Release', 'Keywords'], r'^[^<\x09\x0a\x0d]{0,250}\Z'),
  (['XML_DIZ_INFO', 'Press_Release', 'Headline'], r'^([^<\x09\x0a\x0d]{20,100}|)\Z'),
  (['XML_DIZ_INFO', 'Press_Release', 'Summary'], r'^([^<\x09\x0a\x0d]{20,250}|)\Z'),
  (['XML_DIZ_INFO', 'Press_Release', 'Press_Release'], r'^[^<\x09\x0a\x0d]{0,3000}\Z'),
  (['XML_DIZ_INFO', 'Press_Release', 'Press_Release_Plain'], r'^[^<\x09\x0a\x0d]{0,3000}\Z'),
  (['XML_DIZ_INFO', 'Press_Release', 'Related_URL'], r'^((http|https):\/\/.{0,100}|)\Z'),
  (['XML_DIZ_INFO', 'NewsFeed', 'NewsFeed_Feed_URL'], r'^((http|https):\/\/.{0,100}|)\Z'),
  (['XML_DIZ_INFO', 'NewsFeed', 'NewsFeed_Type'], r'^(RSS 0\.90|RSS 0\.91|RSS 0\.92|RSS 0\.93|RSS 0\.94|RSS 1\.0|RSS 2\.0|Atom 0\.3|Atom 1\.0|)\Z'),
  (['XML_DIZ_INFO', 'NewsFeed', 'NewsFeed_Title'], r'^[^<\x09\x0a\x0d]{0,60}\Z'),
  (['XML_DIZ_INFO', 'NewsFeed', 'NewsFeed_Keywords'], r'^[^<\x09]{0,250}\Z'),
  (['XML_DIZ_INFO', 'NewsFeed', 'NewsFeed_Description_70'], r'^[^<\x09\x0a\x0d]{0,70}\Z'),
  (['XML_DIZ_INFO', 'NewsFeed', 'NewsFeed_Description_250'], r'^[^<\x09\x0a\x0d]{0,250}\Z'),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_ShareIt_Order_Page'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_ShareIt_Vendor_ID'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_ShareIt_Product_ID'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_ShareIt_Maximum_Commission_Rate'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_PayPro_Order_Page'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_PayPro_Vendor_ID'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_PayPro_Product_ID'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_PayPro_Maximum_Commission_Rate'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_Avangate_Order_Page'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_Avangate_Vendor_ID'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_Avangate_Product_ID'], None),
  (['XML_DIZ_INFO', 'Affiliates', 'Affiliates_Avangate_Maximum_Commission_Rate'], None),
  (['XML_DIZ_INFO', 'ASP', 'ASP_Member'], r'^[YyNn]\Z'),
  (['XML_DIZ_INFO', 'ASP', 'ASP_Member_Number'], None),
]

for language in get_pad_languages():
  FIELDS.extend([
    (['XML_DIZ_INFO', 'Program_Descriptions', language, 'Keywords'], r'^[^<\x09]{0,250}\Z'),
    (['XML_DIZ_INFO', 'Program_Descriptions', language, 'Char_Desc_45'], r'^[^<\x09\x0a\x0d]{0,45}\Z'),
    (['XML_DIZ_INFO', 'Program_Descriptions', language, 'Char_Desc_80'], r'^[^<\x09\x0a\x0d]{0,80}\Z'),
    (['XML_DIZ_INFO', 'Program_Descriptions', language, 'Char_Desc_250'], r'^[^<\x09\x0a\x0d]{0,250}\Z'),
    (['XML_DIZ_INFO', 'Program_Descriptions', language, 'Char_Desc_450'], r'^[^<\x09\x0a\x0d]{0,450}\Z'),
    (['XML_DIZ_INFO', 'Program_Descriptions', language, 'Char_Desc_2000'], r'^[^<]{0,2000}\Z'),
  ])

def validate_fields(fields, nodes, filename):
  expected_nodes = set()

  for node_name, fields in itertools.groupby(fields, lambda (path, regex): path[0]):
    expected_nodes.add(node_name)

    regex = None
    nested_fields = []
    for path, regex_ in fields:
      if path == [node_name]:
        regex = regex_
      else:
        nested_fields.append((path[1:], regex_))

    found = False
    for node in nodes:
      if node.nodeName == node_name:
        if found:
          warnings.warn('invalid PAD file (duplicate node)\n'
                        'filename: %s\n'
                        'node:     %s' % (filename, node_name))

        if regex:
          value = ''.join(child.toxml() for child in node.childNodes)
          if not re.match(regex, value):
            warnings.warn('invalid PAD file (invalid value)\n'
                          'filename: %s\n'
                          'node:     %s\n'
                          'value:    %s\n'
                          'regex:    %s' % (filename, node_name, value, regex))

        if nested_fields:
          validate_fields(nested_fields, node.childNodes, filename)

        found = True

    if not found:
      if regex and not re.match(regex, ''):
        warnings.warn('invalid PAD file (missing node)\n'
                      'filename: %s\n'
                      'node:     %s' % (filename, node_name))

      validate_fields(nested_fields, [], filename)

  for node in nodes:
    if node.nodeType == node.COMMENT_NODE:
      continue
    if node.nodeType == node.TEXT_NODE and node.nodeValue.strip() == '':
      continue

    if node.nodeName not in expected_nodes:
      warnings.warn('invalid PAD file (unexpected node)\n'
                    'filename: %s\n'
                    'node:     %s' % (filename, node.nodeName))

def validate_pad(pad, filename):
  validate_fields(FIELDS, minidom.parseString(pad).childNodes, filename)

def print_fields():
  doc = minidom.parse(urllib2.urlopen('http://repository.appvisor.com/padspec/files/padspec40.xml'))

  print '['
  for field in doc.getElementsByTagName('Field'):
    path, regex  = [
      ''.join(node.nodeValue for node in field.getElementsByTagName(name)[0].childNodes)
      for name in ('Path', 'RegEx')
    ]
    print '  (%r, %s),' % (str(path).split('/'), "r'%s'" % regex if regex else 'None')
  print ']'

if __name__ == '__main__':
  print_fields()
