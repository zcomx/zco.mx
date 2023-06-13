#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dal_benchmarks.py

Script to benchmark dal queries.
"""
import argparse
import os
import sys
import traceback
import random
from timeit import Timer
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    Script to benchmark dal queries. Tests are hard coded.

USAGE
    dal_benchmarks.py

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.

    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='dal_benchmarks.py')

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

    LOG.info('Started.')
    ids = [x.id for x in db(db.book).select(db.book.id)]

    class SQLBencher():
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
        sys.exit(1)
