#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
db_io.py

Script to run massive db io for testing.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import time
import logging
from optparse import OptionParser

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')



def man_page():
    """Print manual page-like help"""
    print """
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
    """


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
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) != 1:
        parser.print_help()
        exit(1)


    db.optimize_img_log.truncate()
    for x in range(0, int(args[0])):
        record_id = db.optimize_img_log.insert(
            record_field='_test_',
            record_id=1,
        )
        # db.commit()
        query = (db.optimize_img_log.id == record_id)
        db(query).delete()
        # db.commit()
        time.sleep(int(args[0]))


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
