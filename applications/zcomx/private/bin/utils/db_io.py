#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
db_io.py

Script to run massive db io for testing.
"""
import argparse
import sys
import time
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    db_io.py [OPTIONS] iterations

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

    parser = argparse.ArgumentParser(prog='db_io.py')

    parser.add_argument('number_of_iterations', type=int)

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

    db.optimize_img_log.truncate()
    for _ in range(0, int(args.number_of_iterations)):
        record_id = db.optimize_img_log.insert(image='table.field.aaa.111.jpg')
        # db.commit()
        query = (db.optimize_img_log.id == record_id)
        db(query).delete()
        # db.commit()
        time.sleep(int(args.number_of_iterations))


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
