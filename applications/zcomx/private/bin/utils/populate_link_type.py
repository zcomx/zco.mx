#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
populate_link_type.py

Script to populate the link_type table.
"""
import argparse
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


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
        link_type = db(query).select(limitby=(0, 1)).first()
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
    fmt = '{rid:2s} {code:20s} {label:20s} {url}'
    print(fmt.format(
        rid='ID',
        code='Code',
        label='Label',
        url='Url placeholder',
    ))

    for r in rows:
        print(fmt.format(
            rid=str(r.id),
            code=r.code,
            label=r.label,
            url=r.url_placeholder,
        ))


def man_page():
    """Print manual page-like help"""
    print("""
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.

    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='populate_link_type.py')

    parser.add_argument(
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Truncate table and exit.',
    )
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not create records. Only report what would be done.',
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true', dest='list', default=False,
        help='List existing records and exit.',
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

    if args.list:
        list_records()
        sys.exit(0)

    if args.clear:
        LOG.info('Truncating link_type table')
        db.link_type.truncate()
        db.commit()
        sys.exit(0)

    LOG.info('Started.')
    create_records(dry_run=args.dry_run)
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
