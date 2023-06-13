#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
settings_json_check.py

Script for comparing settings.json to settings.conf or
/srv/http/local/test.conf
"""
import argparse
import os
import sys
import traceback
import json
import unittest
from gluon import *
from gluon.contrib.appconfig import (
    AppConfig,
    AppConfigLoader,
)
from applications.zcomx.modules.argparse.actions import ManPageAction
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
        return {byteify(key): byteify(value) for key, value in element.items()}
    if isinstance(element, list):
        return [byteify(element) for element in element]
    if isinstance(element, str):
        return element
    if isinstance(element, bytes):
        return element.decode('utf-8')
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

    -vv


    --version
        Print the script version.
    Print more verbose output.
    """)


def main():
    """ Main routine.
    Args:
        None.
    Returns:
        None.
    """
    parser = argparse.ArgumentParser(prog='settings_json_check.py')

    parser.add_argument(
        '-d', '--dump', action='store_true',
        dest='dump',
        help='Dump old settings in json format and exit.'
    )
    parser.add_argument(
        '--man', action='store_true',
        dest='man_help',
        help=' '.join((
            'Print manpage-like help and exit.',
            'Manpage help includes examples and notes.'
        ))
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        help='Print messages to stdout'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    if args.man_help:
        parser.print_help()
        print('')
        man_page()
        sys.exit(0)

    LOG.debug('Starting.')

    settings = model_db.settings_loader.settings

    if args.dump:
        print(json.dumps(settings, indent=4, sort_keys=True))
        sys.exit(0)

    configfile = os.path.join(
        current.request.folder, 'private', SETTINGS_FILENAME)

    app_config = AppConfigLoader(configfile=configfile)
    json_settings = byteify({key:value for key, value in app_config.settings.items()})

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
        sys.exit(1)
