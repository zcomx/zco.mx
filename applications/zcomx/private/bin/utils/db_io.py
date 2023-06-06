#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
db_io.py

Script to run massive db io for testing.
"""
import sys
import time
import traceback
from optparse import OptionParser
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

    --vv,
        More verbose. Print debug messages to stdout.
    """)


def main():
    """Main processing."""

    usage = '%prog [options] iterations'
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

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        sys.exit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    db.optimize_img_log.truncate()
    for _ in range(0, int(args[0])):
        record_id = db.optimize_img_log.insert(image='table.field.aaa.111.jpg')
        # db.commit()
        query = (db.optimize_img_log.id == record_id)
        db(query).delete()
        # db.commit()
        time.sleep(int(args[0]))


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
