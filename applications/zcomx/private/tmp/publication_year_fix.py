#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
publication_year_fix.py

Script to set the book.publication_year field based on metadata.
"""
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomx.modules.indicias import \
    PublicationMetadata
from applications.zcomx.modules.utils import \
    entity_to_row

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    publication_year_fix.py

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
    ids = [x.id for x in db(db.book).select(db.book.id)]
    for book_id in ids:
        book_record = entity_to_row(db.book, book_id)
        if not book_record:
            raise LookupError('Book not found, id: {i}'.format(i=book_id))
        meta = PublicationMetadata(book_record)
        meta.load()
        try:
            publication_year = meta.publication_year()
        except ValueError:
            continue        # This is expected if the metadata is not set.

        if book_record.publication_year == publication_year:
            continue
        LOG.debug('Updating: %s to %s', book_record.name, publication_year)
        book_record.update_record(publication_year=publication_year)
        db.commit()
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
