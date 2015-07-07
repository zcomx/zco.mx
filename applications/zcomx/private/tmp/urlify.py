#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
urlify.py

Script to test urlify commands.
"""
import logging
import sys
import traceback
from gluon import *
from optparse import OptionParser
from gluon.validators import urlify

VERSION = 'Version 0.1'

LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    urlify.py

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
    )

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    LOG.info('Started.')

    x = urlify('John Smith')
    print 'FIXME x: {var}'.format(var=x)

    x = urlify('Jøhn Smith')
    print 'FIXME x: {var}'.format(var=x)

    y = db(db.creator.name_for_url == x).select().first()
    print 'FIXME y: {var}'.format(var=y)
    print 'FIXME db._lastsql: {var}'.format(var=db._lastsql)



    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
