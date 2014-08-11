#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
tally_book_ratings.py

Script to tally the yearly and monthly contributions, ratings, and views for
each book.
"""
import datetime
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')

PERIODS = {
        # name: days
        'month': 30,
        'year': 365,
        }

RATINGS = [
    # (book field, data field, period, function)
    (db.book.contributions_year, db.contribution.amount, 'year', 'sum'),
    (db.book.contributions_month, db.contribution.amount, 'month', 'sum'),
    (db.book.rating_year, db.rating.amount, 'year', 'avg'),
    (db.book.rating_month, db.rating.amount, 'month', 'avg'),
    (db.book.views_year, db.book_view.id, 'year', 'count'),
    (db.book.views_month, db.book_view.id, 'month', 'count'),
    ]


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    tally_book_ratings.py
    tally_book_ratings.py --vv          # Verbose output

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

    parser.add_option('--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
        )
    parser.add_option('-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
        )
    parser.add_option('--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
        )

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [h.setLevel(level) for h in LOG.handlers \
                if h.__class__ == logging.StreamHandler]

    LOG.info('Started.')

    for book in db(db.book).select(db.book.ALL):
        LOG.debug('book.name: {var}'.format(var=book.name))
        book_query = (db.book.id == book.id)
        for rating in RATINGS:
            field, data_field, period, func = rating
            LOG.debug('Updating: {f}'.format(f=field))
            data_table = data_field.table
            days = PERIODS[period]
            min_date = datetime.datetime.now() - datetime.timedelta(days=days)
            time_query = (data_table.time_stamp >= min_date)
            if func == 'sum':
                tally = data_field.sum()
            elif func == 'avg':
                tally = data_field.avg()
            elif func == 'count':
                tally = data_field.count()
            query = book_query & time_query
            rows = db(query).select(
                tally,
                left=[data_table.on(data_table.book_id == db.book.id)],
                groupby=data_table.book_id
            ).first()
            value = rows[tally] or 0 if rows else 0
            db(db.book.id == book.id).update(**{field.name: value})
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
