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

ISO2PAD = {
  'ab': 'Abkhazian',
  'aa': 'Afar',
  'af': 'Afrikaans',
  'sq': 'Albanian',
  'am': 'Amharic',
  'ar': 'Arabic',
  'hy': 'Armenian',
  'as': 'Assamese',
  'ay': 'Aymara',
  'az': 'Azerbaijani',
  'ba': 'Bashkir',
  'eu': 'Basque',
  'be': 'Byelorussian',
  'bn': 'Bengali',
  'bh': 'Bihari',
  'bi': 'Bislama',
  'br': 'Breton',
  'bg': 'Bulgarian',
  'my': 'Burmese',
  'ca': 'Catalan',
  'zh': 'Chinese',
  'zh-cn': 'ChineseSimplified',
  'zh-tw': 'ChineseTraditional',
  'co': 'Corsican',
  'hr': 'Croatian',
  'cs': 'Czech',
  'da': 'Danish',
  'nl': 'Dutch',
  'en': 'English',
  'eo': 'Esperanto',
  'et': 'Estonian',
  'fo': 'Faeroese',
  'fj': 'Fiji',
  'fi': 'Finnish',
  'fr': 'French',
  'gl': 'Galician',
  'ka': 'Georgian',
  'de': 'German',
  'el': 'Greek',
  'gn': 'Guarani',
  'gu': 'Gujarati',
  'ha': 'Hausa',
  'he': 'Hebrew',
  'hi': 'Hindi',
  'hu': 'Hungarian',
  'ia': 'Interlingua',
  'id': 'Indonesian',
  'ie': 'Interlingue',
  'ga': 'Irish',
  'ik': 'Inupiak',
  'is': 'Icelandic',
  'it': 'Italian',
  'ja': 'Japanese',
  'jv': 'Javanese',
  'kl': 'Greenlandic',
  'kn': 'Kannada',
  'ks': 'Kashmiri',
  'kk': 'Kazakh',
  'km': 'Cambodian',
  'rw': 'Kinyarwanda',
  'ky': 'Kirghiz',
  'ko': 'Korean',
  'ku': 'Kurdish',
  'la': 'Latin',
  'ln': 'Lingala',
  'lo': 'Laothian',
  'lt': 'Lithuanian',
  'lv': 'Latvian',
  'mk': 'Macedonian',
  'mg': 'Malagasy',
  'ms': 'Malay',
  'ml': 'Malayalam',
  'mt': 'Maltese',
  'mi': 'Maori',
  'mr': 'Marathi',
  'mn': 'Mongolian',
  'na': 'Nauru',
  'ne': 'Nepali',
  'no': 'Norwegian',
  'oc': 'Occitan',
  'om': 'Oromo',
  'or': 'Oriya',
  'pa': 'Punjabi',
  'fa': 'Persian',
  'pl': 'Polish',
  'ps': 'Pashto',
  'pt': 'Portuguese',
  'qu': 'Quechua',
  'rm': 'Rhaeto-Romance',
  'rn': 'Kirundi',
  'ro': 'Romanian',
  'ru': 'Russian',
  'sa': 'Sanskrit',
  'sd': 'Sindhi',
  'sm': 'Samoan',
  'sg': 'Sangro',
  'sr': 'Serbian',
  'gd': 'Gaelic',
  'sn': 'Shona',
  'si': 'Singhalese',
  'sk': 'Slovak',
  'sl': 'Slovenian',
  'so': 'Somali',
  'st': 'Sesotho',
  'es': 'Spanish',
  'sw': 'Swahili',
  'ss': 'Siswati',
  'sv': 'Swedish',
  'sh': 'Serbo-Croatian',
  'ta': 'Tamil',
  'te': 'Telugu',
  'tg': 'Tajik',
  'th': 'Thai',
  'ti': 'Tigrinya',
  'bo': 'Tibetan',
  'tk': 'Turkmen',
  'tl': 'Tagalog',
  'tn': 'Setswana',
  'to': 'Tonga',
  'tr': 'Turkish',
  'ts': 'Tsonga',
  'tt': 'Tatar',
  'tw': 'Twi',
  'uk': 'Ukrainian',
  'ur': 'Urdu',
  'uz': 'Uzbek',
  'vi': 'Vietnamese',
  'vo': 'Volapuk',
  'cy': 'Welsh',
  'wo': 'Wolof',
  'fy': 'Frisian',
  'xh': 'Xhosa',
  'yi': 'Yiddish',
  'yo': 'Yoruba',
  'zu': 'Zulu',
}

def iso2pad(iso_languages):
  pad_languages = []
  has_other = False

  for iso in iso_languages:
    iso = iso.replace('_', '-').lower()

    pad = ISO2PAD.get(iso)
    if not pad:
      pad = ISO2PAD.get(iso.split('-')[0])
      if not pad:
        has_other = True
        continue

    if pad not in pad_languages:
      pad_languages.append(pad)

  pad_languages.sort()
  if has_other:
    pad_languages.append('Other')

  return pad_languages
