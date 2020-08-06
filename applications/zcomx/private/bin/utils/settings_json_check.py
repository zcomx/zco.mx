#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
settings_json_check.py

Script for comparing settings.json to settings.conf or
/srv/http/local/test.conf
"""

import os
import sys
import traceback
import json
import unittest
from optparse import OptionParser
from gluon import *
from gluon.contrib.appconfig import AppConfig
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
SETTINGS_FILENAME = 'settings.json'


class TestComparer(unittest.TestCase):
    """Dummy TestCase so assert* methods available."""

    maxDiff = None

    def runTest(self):
        """runTest"""
        # pylint: disable=invalid-name
        self._testFunc()


def byteify(element):
    """Converts unicode elements of dict or list into str.
    # Source:
    # http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-ones-from-json-in-python
    """
    if isinstance(element, dict):
        return {byteify(key): byteify(value)
                for key, value in element.items()}
    elif isinstance(element, list):
        return [byteify(element) for element in element]
    elif isinstance(element, str):
        return element.encode('utf-8')
    else:
        return element


def is_same(item1, item2):
    """Compare two items."""
    comparer = TestComparer()
    comparer.assertEqual(item1, item2)

    assert sorted(item1) == sorted(item2)


def man_page():
    """Print manual page-like help"""
    print("""
GENERAL USAGE

    settings_json_check.py

OPTIONS
    -d, --dump
        Dump the old settings in json format and exit.

    --man

    Print manpage-like help.

    -v, --verbose

    Print verbose output.

    --vv

    Print more verbose output.
    """)


def main():
    """ Main routine.
    Args:
        None.
    Returns:
        None.
    """

    # E1101 *%s %r has no %r member*
    # pylint: disable=E1101

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-d', '--dump', action='store_true',
        dest='dump',
        help='Dump old settings in json format and exit.'
    )
    parser.add_option(
        '--man', action='store_true',
        dest='man_help',
        help=' '.join((
            'Print manpage-like help and exit.',
            'Manpage help includes examples and notes.'
        ))
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true',
        dest='verbose',
        help='Print messages to stdout'
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose',
    )

    (options, unused_args) = parser.parse_args()

    set_cli_logging(LOG, options.verbose, options.vv)

    if options.man_help:
        parser.print_help()
        print('')
        man_page()
        quit(0)

    LOG.debug('Starting.')

    settings = model_db.settings_loader.settings

    if options.dump:
        print(json.dumps(settings, indent=4, sort_keys=True))
        exit(0)

    configfile = os.path.join(
        current.request.folder, 'private', SETTINGS_FILENAME)

    json_settings = byteify(AppConfig(configfile=configfile, reload=True))

    is_same(settings['auth'], json_settings['web2py']['auth']['settings'])
    is_same(settings['mail'], json_settings['web2py']['mail']['settings'])
    is_same(settings['response'], json_settings['web2py']['response'])
    is_same(settings['local'], json_settings['app'])

    LOG.debug('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
