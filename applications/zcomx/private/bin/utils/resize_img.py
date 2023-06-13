#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
resize_images.py

Script to simulate resize_img.sh from python.
"""
import argparse
import os
import shutil
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.images import ResizeImg
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.


NOTES:

    The original file is preserved.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='resize_img.py')

    parser.add_argument(
        'filenames',
        nargs='+',
        metavar='filename [filename ...]'
    )

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-t', '--tmp-dir',
        dest='tmp_dir', default='/tmp/resize_img_py',
        help='Working directory. Default /tmp/resize_img_py',
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

    LOG.info('Started.')
    # copy the file to a temp name.
    if not os.path.exists(args.tmp_dir):
        os.makedirs(args.tmp_dir)

    for filename in args.filenames:
        base = os.path.basename(filename)
        dest_filename = os.path.join(args.tmp_dir, base)
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
        sys.exit(1)
