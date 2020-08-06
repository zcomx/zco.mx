#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
create_img.py

Script to create images.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404

import sys
import traceback
from optparse import OptionParser
from PIL import Image
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def create_img(filename, dimensions, color):
    """Create an image.

    Args:
        filename: string, name of output file
        dimenstions: tuple, (width, height)
        color: color for image, see PIL.Image.new()
    """
    im = Image.new('RGB', dimensions, color)
    with open(filename, 'wb') as f:
        im.save(f)


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    create_img.py [OPTIONS] path/to/outfile.jpg width height

OPTIONS
    -c, --colour
        The colour of the image. Default: black.

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """)


def main():
    """Main processing."""

    usage = '%prog [options] path/to/outfile.jpg width height'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-c', '--colour',
        dest='colour', default='#000000',
        help='Specify the colour.',
    )
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

    set_cli_logging(LOG, options.verbose, options.vv)

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

    create_img(args[0], (width, height), options.colour)

if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
