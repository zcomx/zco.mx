#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
resize_images.py

Script to simulate resize_img.sh from python.
"""

import os
import shutil
import sys
import traceback
from optparse import OptionParser
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.images import ResizeImg
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
resize_img.py - Simulate resize_img.sh with python.

USAGE
    resize_img.py [OPTIONS] FILE

    resize_images.py file.jpg

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -t PATH, --tmp-dir=PATH
        Set PATH as the working directory. Original files are copied there
        before processing. If PATH doesn't exist, it is created.
        Default /tmp/resize_img_py.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.


NOTES:

    The original file is preserved.
    """)


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
        '-t', '--tmp-dir',
        dest='tmp_dir', default='/tmp/resize_img_py',
        help='Working directory. Default /tmp/resize_img_py',
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

    if len(args) < 1:
        parser.print_help()
        exit(1)

    LOG.info('Started.')
    # copy the file to a temp name.
    if not os.path.exists(options.tmp_dir):
        os.makedirs(options.tmp_dir)

    for filename in args:
        base = os.path.basename(filename)
        dest_filename = os.path.join(options.tmp_dir, base)
        shutil.copy(filename, dest_filename)

        resize_img = ResizeImg(dest_filename)
        resize_img.run()
        for size, name in list(resize_img.filenames.items()):
            LOG.info('{size}: {name}'.format(size=size, name=name))
    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
