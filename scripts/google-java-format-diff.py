#!/usr/bin/env python2.7
#
#===- google-java-format-diff.py - google-java-format Diff Reformatter -----===#
#
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
#===------------------------------------------------------------------------===#

"""
google-java-format Diff Reformatter
============================

This script reads input from a unified diff and reformats all the changed
lines. This is useful to reformat all the lines touched by a specific patch.
Example usage for git/svn users:

  git diff -U0 HEAD^ | google-java-format-diff.py -p1 -i
  svn diff --diff-cmd=diff -x-U0 | google-java-format-diff.py -i

For perforce users:

  P4DIFF="git --no-pager diff --no-index" p4 diff | ./google-java-format-diff.py -i -p7

"""

import argparse
import difflib
import re
import string
import subprocess
import StringIO
import sys
from distutils.spawn import find_executable

def main():
  parser = argparse.ArgumentParser(description=
                                   'Reformat changed lines in diff. Without -i '
                                   'option just output the diff that would be '
                                   'introduced.')
  parser.add_argument('-i', action='store_true', default=False,
                      help='apply edits to files instead of displaying a diff')

  parser.add_argument('-p', metavar='NUM', default=0,
                      help='strip the smallest prefix containing P slashes')
  parser.add_argument('-regex', metavar='PATTERN', default=None,
                      help='custom pattern selecting file paths to reformat '
                      '(case sensitive, overrides -iregex)')
  parser.add_argument('-iregex', metavar='PATTERN', default=r'.*\.java',
                      help='custom pattern selecting file paths to reformat '
                      '(case insensitive, overridden by -regex)')
  parser.add_argument('-v', '--verbose', action='store_true',
                      help='be more verbose, ineffective without -i')
  parser.add_argument('-a', '--aosp', action='store_true',
                      help='use AOSP style instead of Google Style (4-space indentation)')
  parser.add_argument('--skip-sorting-imports', action='store_true',
                      help='do not fix the import order')
  parser.add_argument('--skip-removing-unused-imports', action='store_true',
                      help='do not remove ununsed imports')
  parser.add_argument(
      '--skip-javadoc-formatting',
      action='store_true',
      default=False,
      help='do not reformat javadoc')
  parser.add_argument('-b', '--binary', help='path to google-java-format binary')
  parser.add_argument('--google-java-format-jar', metavar='ABSOLUTE_PATH', default=None,
                      help='use a custom google-java-format jar')

  args = parser.parse_args()

  # Extract changed lines for each file.
  filename = None
  lines_by_file = {}

  for line in sys.stdin:
    match = re.search('^\+\+\+\ (.*?/){%s}(\S*)' % args.p, line)
    if match:
      filename = match.group(2)
    if filename == None:
      continue

    if args.regex is not None:
      if not re.match('^%s$' % args.regex, filename):
        continue
    else:
      if not re.match('^%s$' % args.iregex, filename, re.IGNORECASE):
        continue

    match = re.search('^@@.*\+(\d+)(,(\d+))?', line)
    if match:
      start_line = int(match.group(1))
      line_count = 1
      if match.group(3):
        line_count = int(match.group(3))
      if line_count == 0:
        continue
      end_line = start_line + line_count - 1;
      lines_by_file.setdefault(filename, []).extend(
          ['-lines', str(start_line) + ':' + str(end_line)])

  if args.binary:
    base_command = [args.binary]
  elif args.google_java_format_jar:
    base_command = ['java', '-jar', args.google_java_format_jar]
  else:
    binary = find_executable('google-java-format') or '/usr/bin/google-java-format'
    base_command = [binary]

  # Reformat files containing changes in place.
  for filename, lines in lines_by_file.iteritems():
    if args.i and args.verbose:
      print 'Formatting', filename
    command = base_command[:]
    if args.i:
      command.append('-i')
    if args.aosp:
      command.append('--aosp')
    if args.skip_sorting_imports:
      command.append('--skip-sorting-imports')
    if args.skip_removing_unused_imports:
      command.append('--skip-removing-unused-imports')
    if args.skip_javadoc_formatting:
      command.append('--skip-javadoc-formatting')
    command.extend(lines)
    command.append(filename)
    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                         stderr=None, stdin=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
      sys.exit(p.returncode);

    if not args.i:
      with open(filename) as f:
        code = f.readlines()
      formatted_code = StringIO.StringIO(stdout).readlines()
      diff = difflib.unified_diff(code, formatted_code,
                                  filename, filename,
                                  '(before formatting)', '(after formatting)')
      diff_string = string.join(diff, '')
      if len(diff_string) > 0:
        sys.stdout.write(diff_string)

if __name__ == '__main__':
  main()
