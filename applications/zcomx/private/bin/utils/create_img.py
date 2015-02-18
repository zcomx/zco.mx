#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
create_img.py

Script to create images.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
from PIL import Image
from optparse import OptionParser

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def create_img(filename, dimensions):
    """Create an image.

    Args:
        filename: string, name of output file
        dimenstions: tuple, (width, height)
    """
    im = Image.new('RGB', dimensions)
    with open(filename, 'wb') as f:
        im.save(f)


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    create_img.py [OPTIONS] path/to/outfile.jpg width height

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

    usage = '%prog [options] path/to/outfile.jpg width height'
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

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) < 3:
        parser.print_help()
        exit(1)

    try:
        width = int(args[1])
    except (TypeError, ValueError):
        parser.print_help()
        exit(1)

    try:
        height = int(args[2])
    except (TypeError, ValueError):
        parser.print_help()
        exit(1)

    create_img(args[0], (width, height))

if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
