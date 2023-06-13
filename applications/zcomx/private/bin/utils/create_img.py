#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
create_img.py

Script to create images.
"""
import argparse
import sys
import traceback
from PIL import Image
from applications.zcomx.modules.argparse.actions import ManPageAction
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='create_img.py')

    parser.add_argument('outfile')
    parser.add_argument('width')
    parser.add_argument('height')

    parser.add_argument(
        '-c', '--colour',
        dest='colour', default='#000000',
        help='Specify the colour.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    try:
        width = int(args.width)
    except (TypeError, ValueError):
        parser.print_help()
        sys.exit(1)

    try:
        height = int(args.height)
    except (TypeError, ValueError):
        parser.print_help()
        sys.exit(1)

    create_img(args.outfile, (width, height), args.colour)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
