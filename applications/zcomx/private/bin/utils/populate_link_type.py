#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
populate_link_type.py

Script to populate the link_type table.
"""
import logging
import os
from gluon import *
from gluon.shell import env
from optparse import OptionParser

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')

TYPES = [
    {
        'code': 'buy_book',
        'label': 'buy this book',
        'name_placeholder': 'Name-of-link',
        'url_placeholder': 'http://etsy.com/title-of-book',
    },
    {
        'code': 'creator_page',
        'label': 'links',
        'name_placeholder': 'eg. patreon',
        'url_placeholder': 'http://patreon.com/name',
    },
    {
        'code': 'book_review',
        'label': 'reviews',
        'name_placeholder': 'Name-of-reviewer',
        'url_placeholder': 'http://reviewer.com/review-link',
    },
    {
        'code': 'creator_article',
        'label': 'articles',
        'name_placeholder': 'Name-of-writer',
        'url_placeholder': 'http://writer.com/article-link',
    },
]


def create_records(dry_run=False):
    """Create records."""
    for record in TYPES:
        query = (db.link_type.code == record['code'])
        link_type = db(query).select().first()
        if not link_type:
            LOG.info(
                '%sCreating record: %s',
                '!! DRY RUN !! ' if dry_run else '',
                record['code']
            )
            if not dry_run:
                db.link_type.insert(code=record['code'])
                db.commit()
        LOG.info(
            '%sUpdating record: %s',
            '!! DRY RUN !! ' if dry_run else '',
            record['code']
        )
        if not dry_run:
            db(query).update(**record)
            db.commit()


def list_records():
    """List records."""
    rows = db().select(db.link_type.ALL)
    for r in rows:
        print '{rid} {name:20s} {seq}'.format(
            rid=r.id, name=r.name, seq=r.sequence)


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    populate_link_type.py [OPTIONS]

    This script is safe to be rerun without the -c, --clear option.
    The -c, --clear option is *not* safe. It may corrupt references to
    the link_type table.


OPTIONS
    -c, --clear
        Truncate the link_type table and exit.

    -d, --dry-run
        Do not create records, only report what would be done.

    -h, --help
        Print a brief help.

    -l, --list
        List existing list_types.

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
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Truncate table and exit.',
    )
    parser.add_option(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not create records. Only report what would be done.',
    )
    parser.add_option(
        '-l', '--list',
        action='store_true', dest='list', default=False,
        help='List existing records and exit.',
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

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if options.list:
        list_records()
        quit(0)

    if options.clear:
        LOG.info('Truncating link_type table')
        db.link_type.truncate()
        db.commit()
        quit(0)

    if len(args) > 1:
        print parser.print_help()
        quit(1)

    LOG.info('Started.')
    create_records(dry_run=options.dry_run)
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
