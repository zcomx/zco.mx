#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
resize_images.py

Script to simulate resize_img.sh from python.
"""
import logging
import os
import shutil
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomx.modules.images import ResizeImg

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
resize_img.py - Simulate resize_img.sh with python.

USAGE
    resize_img.py [OPTIONS] FILE

    resize_images.py file.jpg

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.


NOTES:

    The original file is preserved.
    """


def main():
    """Main processing."""

    usage = '%prog [options] file'
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

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.info('Started.')
    # copy the file to a temp name.
    image_dir = '/tmp/resize_img_py'
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    base = os.path.basename(args[0])
    dest_filename = os.path.join(image_dir, base)
    shutil.copy(args[0], dest_filename)

    resize_img = ResizeImg(dest_filename)
    resize_img.run(nice=True)
    for size, name in resize_img.filenames.items():
        LOG.info('{size}: {name}'.format(size=size, name=name))
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
