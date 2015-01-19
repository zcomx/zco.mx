#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
indicia_png.py

Script to create indicia png files for a creator or a book.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
import shutil
from PIL import Image
from optparse import OptionParser
from applications.zcomx.modules.indicias import \
    BookIndiciaPagePng, \
    CreatorIndiciaPagePng
from applications.zcomx.modules.utils import entity_to_row

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
    indicia_png.py [OPTIONS] id|name

    indicia_png.py 64                       # Create png for book by id
    indicia_png.py 'Test Do Not Delete'     # Create png for book by name
    indicia_png.py -c 101                   # Create png for creator by id
    indicia_png.py -c 'Charles Forsman'     # Create png for creator by name
    indicia_png.py 64 --out /path/to/file.png  # Specify the output file.
    indicia_png.py 64 --landscape           # Orientation is landscape

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

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] id|name'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-c', '--creator',
        action='store_true', dest='creator', default=False,
        help='Create indicia png for a creator.',
    )
    parser.add_option(
        '-l', '--landscape',
        action='store_true', dest='landscape', default=False,
        help='Png orientation=landscape. Default: portrait',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-o', '--output',
        dest='output', default=None,
        help='Create png file with this name.',
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

    if len(args) < 1:
        parser.print_help()
        exit(1)

    record = None
    record_id = None
    name = None
    try:
        record_id = int(args[0])
    except (TypeError, ValueError):
        name = args[0]

    table = db.creator if options.creator else db.book

    if record_id:
        record = entity_to_row(table, record_id)
        if not record:
            print 'No {t} found, id: {i}'.format(t=str(table), i=record_id)
            quit(1)
    else:
        if options.creator:
            query = (db.auth_user.name == name)
            rows = db(query).select(
                left=db.creator.on(
                    db.creator.auth_user_id == db.auth_user.id),
            )
        else:
            query = (db.book.name == name)
            rows = db(query).select()

        if not rows:
            print 'No {t} found, name: {n}'.format(t=str(table), n=name)
            quit(1)
        if len(rows) > 1:
            print 'Multiple {t} matches, use {t} id:'.format(t=str(table))
            for r in rows:
                print 'id: {i}'.format(i=r.id)
            quit(1)
        record = rows[0]

    obj_class = CreatorIndiciaPagePng if options.creator \
        else BookIndiciaPagePng

    orientation = 'landscape' if options.landscape else 'portrait'

    png_page = obj_class(record)
    png = png_page.create(orientation=orientation)
    if options.output:
        shutil.copy(png, options.output)


if __name__ == '__main__':
    main()
