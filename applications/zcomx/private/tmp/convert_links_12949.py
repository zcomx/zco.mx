#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
convert_links_12949.py

Script to convert links from book_to_link/creator_to_link to new format.
See mod 12949.
"""
import logging
import sys
import traceback
from gluon import *
from optparse import OptionParser
from applications.zcomx.modules.link_types import LinkType

VERSION = 'Version 0.1'

LOG = logging.getLogger('cli')


def convert_book_links():
    """Convert book links."""
    link_type_code = 'buy_book'
    link_type = LinkType.by_code(link_type_code)
    if not link_type:
        LOG.error('Link type not found, code: %s', link_type_code)
        return

    for book_to_link in db(db.book_to_link).select():
        LOG.debug('Updating book_to_link: %s', book_to_link.id)
        query = (db.link.id == book_to_link.link_id)
        link = db(query).select().first()
        if not link:
            LOG.error('Link not found, id: %s', book_to_link.link_id)
            continue

        data = dict(
            link_type_id=link_type.id,
            record_table='book',
            record_id=book_to_link.book_id,
            order_no=book_to_link.order_no,
        )
        link.update_record(**data)
        db.commit()


def convert_creator_links():
    """Convert creator links."""
    link_type_code = 'creator_link'
    link_type = LinkType.by_code(link_type_code)
    if not link_type:
        LOG.error('Link type not found, code: %s', link_type_code)
        return

    for creator_to_link in db(db.creator_to_link).select():
        LOG.debug('Updating creator_to_link: %s', creator_to_link.id)
        query = (db.link.id == creator_to_link.link_id)
        link = db(query).select().first()
        if not link:
            LOG.error('Link not found, id: %s', creator_to_link.link_id)
            continue

        data = dict(
            link_type_id=link_type.id,
            record_table='creator',
            record_id=creator_to_link.creator_id,
            order_no=creator_to_link.order_no,
        )
        link.update_record(**data)
        db.commit()


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    convert_links_12949.py

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

    convert_book_links()
    convert_creator_links()

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
