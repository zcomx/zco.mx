#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
dal_benchmarks.py

Script to benchmark dal queries.
"""

import os
import sys
import traceback
import random
from optparse import OptionParser
from timeit import Timer
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    dal_tests.py


OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """)


def main():
    """Main processing."""

    usage = '%prog [options] [file...]'
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

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.info('Started.')
    ids = [x.id for x in db(db.book).select(db.book.id)]

    class SQLBencher(object):
        """Class representing an SQL query benchmarker."""

        count = 0

        def all_func(self):
            """Select all fields."""
            book_id = ids[self.count]
            query = (db.book.id == book_id)
            db(query).select()
            self.increment()

        def few_func(self):
            """Select a few fields."""
            book_id = ids[self.count]
            query = (db.book.id == book_id)
            db(query).select(db.book.id, db.book.name, db.book.release_date)
            self.increment()

        def only_id(self):
            """Select only the id field."""
            book_id = ids[self.count]
            query = (db.book.id == book_id)
            db(query).select(db.book.id)
            self.increment()

        def increment(self):
            """Increment counter."""
            self.count += 1
            if self.count > len(ids):
                self.count = 0

        def run(self):
            """Run tests."""
            test_runs = 100
            for func in [self.all_func, self.only_id, self.few_func]:
                self.reset()
                t = Timer(func)
                print(t.timeit(number=test_runs))

        def reset(self):
            """Reset counter and shuffle ids."""
            self.count = 0
            random.shuffle(ids)

    bencher = SQLBencher()
    bencher.run()

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
