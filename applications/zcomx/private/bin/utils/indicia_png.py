#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
indicia_png.py

Script to create indicia png files for a creator or a book.
"""
import argparse
import os
import shutil
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.indicias import (
    BookIndiciaPagePng,
    CreatorIndiciaPagePng,
    IndiciaPage,
    IndiciaSh,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def create_generic_png(args):
    """Create a generic png file.

    Args:
        args: dict of argparse args

    """
    creator_id = 0

    indicia = IndiciaPage(None)
    meta_text = indicia.licence_text(template_field='template_img')
    metadata_filename = os.path.join('/tmp', 'meta.txt')
    with open(metadata_filename, 'w', encoding='utf-8') as f:
        f.write(meta_text)

    indicia_filename = os.path.join(
        request.folder,
        *IndiciaPage.default_indicia_paths
    )
    indicia_sh = IndiciaSh(
        '{c:03d}'.format(c=creator_id),
        metadata_filename,
        indicia_filename,
        landscape=args.landscape
    )
    indicia_sh.run()
    if args.output:
        shutil.copy(indicia_sh.png_filename, args.output)
    else:
        shutil.copy(indicia_sh.png_filename, os.getcwd())
    os.unlink(metadata_filename)


def create_png(record, args):
    """Create a png file.

    Args:
        record: Row instance representing record.
        args: dict of argparse args

    """
    obj_class = CreatorIndiciaPagePng if args.creator \
        else BookIndiciaPagePng

    orientation = 'landscape' if args.landscape else 'portrait'
    png_page = obj_class(record)
    png = png_page.create(orientation=orientation)
    if args.output:
        shutil.copy(png, args.output)
    else:
        shutil.copy(png, os.getcwd())


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    This script creates indicia png files for a creator or a book.
USAGE
    indicia_png.py [OPTIONS] id|name

    indicia_png.py 64                       # Create png for book by id
    indicia_png.py 'Test Do Not Delete'     # Create png for book by name
    indicia_png.py -c 101                   # Create png for creator by id
    indicia_png.py -c 'Charles Forsman'     # Create png for creator by name
    indicia_png.py 64 --out /path/to/file.png  # Specify the output file.
    indicia_png.py 64 --landscape           # Orientation is landscape
    indicia_png.py -c 0                     # Create generic png

OPTIONS
    -c, --creator
        Create the png file for a creator.

    -h, --help
        Print a brief help.

    -l, --landscape
        Create the png with landscape orientation. By default, the portrait
        orientation png is created.

    --man
        Print man page-like help.

    -o PATH, --output=PATH
        By default, the png file is named indicia.png in the current working
        directory. With this option, name the created png file PATH.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='indicia_png.py')

    parser.add_argument('name', metavar='id|name')

    parser.add_argument(
        '-c', '--creator',
        action='store_true', dest='creator', default=False,
        help='Create indicia png for a creator.',
    )
    parser.add_argument(
        '-l', '--landscape',
        action='store_true', dest='landscape', default=False,
        help='Png orientation=landscape. Default: portrait',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-o', '--output',
        dest='output', default=None,
        help='Create png file with this name.',
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

    record = None
    record_id = None
    name = None
    try:
        record_id = int(args[0])
    except (TypeError, ValueError):
        name = args.name

    table = db.creator if args.creator else db.book
    record_class = Creator if args.creator else Book

    if record_id is not None:
        if not args.creator or record_id != 0:
            try:
                record = record_class.from_id(record_id)
            except LookupError:
                print(
                    'No {t} found, id: {i}'.format(t=str(table), i=record_id))
                sys.exit(1)
    else:
        if args.creator:
            query = (db.auth_user.name == name)
            rows = db(query).select(
                left=db.creator.on(
                    db.creator.auth_user_id == db.auth_user.id),
            )
        else:
            query = (db.book.name == name)
            rows = db(query).select()

        if not rows:
            print('No {t} found, name: {n}'.format(t=str(table), n=name))
            sys.exit(1)
        if len(rows) > 1:
            print('Multiple {t} matches, use {t} id:'.format(t=str(table)))
            for r in rows:
                print('id: {i}'.format(i=r.id))
            sys.exit(1)
        record = record_class.from_id(rows[0].id)

    if args.creator and record_id == 0:
        create_generic_png(args)
    else:
        create_png(record, args)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
