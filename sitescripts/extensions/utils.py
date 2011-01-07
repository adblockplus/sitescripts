# coding: utf-8

import re

def compareVersionParts(part1, part2):
  def convertInt(value, default):
    try:
      return int(value)
    except ValueError:
      return default

  def convertVersionPart(part):
    if part == '*':
      # Special case - * is interpreted as Infinity
      return (1.0e300, '', 0, '')
    else:
      match = re.match(r'^(\d*)(\D*)(\d*)(.*)', part)
      a, b, c, d = (convertInt(match.group(1), 0), match.group(2), convertInt(match.group(3), 0), match.group(4))
      if b == '+':
        # Another special case - "2+" is the same as "3pre"
        a += 1
        b = 'pre'
      return (a, b, c, d)

  def compareStringPart(str1, str2):
    if str1 == str2:
      return 0

    # Missing strings are always larger
    if str1 == '':
      return 1
    if str2 == '':
      return -1

    if str1 < str2:
      return -1
    if str1 > str2:
      return 1
    raise Exception('This should never run, something is wrong')

  a1, b1, c1, d1 = convertVersionPart(part1)
  a2, b2, c2, d2 = convertVersionPart(part2)
  return (a1 - a2) or compareStringPart(b1, b2) or (c1 - c2) or compareStringPart(d1, d2)

def compareVersions(version1, version2):
  """
    Compares two version numbers according to the rules outlined on
    https://developer.mozilla.org/en/XPCOM_Interface_Reference/nsIVersionComparator.
    Returns a value smaller than 0 if first version number is smaller,
    larger than 0 if it is bigger, and 0 if the version numbers are effectively
    equal.
  """

  parts1 = version1.split('.')
  parts2 = version2.split('.')
  for i in range(0, max(len(parts1), len(parts2))):
    part1 = ''
    part2 = ''
    if i < len(parts1):
      part1 = parts1[i]
    if i < len(parts2):
      part2 = parts2[i]
    result = compareVersionParts(part1, part2)
    if result != None and result != 0:
      return result
  return 0
