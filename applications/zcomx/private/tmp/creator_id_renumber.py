#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
creator_id_renumber.py

Script to renumber the creator ids.
"""
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

IDS = {
    'Jim Karsten': 98,
    "Sinus O'Gynus": 99,
    'Charles Forsman': 101,
    'Kevin Huizenga': 102,
    'Jordan Crane': 103,
    'Marc Bell': 104,
}


class Creator(object):
    """Class representing a Creator"""

    def __init__(self, name, old_id, new_id):
        """Constructor

        Args:
            name: string, creator name_for_url,
            old_id: integer, original id
            new_id: integer, new id
        """
        self.name = name,
        self.old_id = old_id
        self.new_id = new_id

    def update_tables(self):
        """Update all tables with creator ids."""

        for table in ['book', 'creator_to_link']:
            query = (db[table].creator_id == self.old_id)
            db(query).update(creator_id=self.new_id)
            db.commit()


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    creator_id_renumber.py
    WARNING: This will reset the ids of creators.

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
    db.define_table('creator_bak', db.creator, migrate=True)
    count_bak = db(db.creator_bak).count()      # Access table so it is created
    if count_bak > 0:
        db.creator_bak.truncate()

    next_id = max(IDS.values()) + 1
    creators = []
    for creator in db(db.creator).select():
        db.creator_bak.insert(**creator.as_dict())
        db.commit()
        if creator.name_for_url in IDS:
            new_id = IDS[creator.name_for_url]
        else:
            new_id = next_id
            next_id += 1
        creators.append(Creator(creator.name_for_url, int(creator.id), new_id))

    count = db(db.creator).count()
    count_bak = db(db.creator_bak).count()
    if not count > 0 or count != count_bak or len(creators) != count:
        LOG.error('Invalid record counts. Aborting.')
        quit(1)

    new_ids = [x.new_id for x in creators]
    if len(new_ids) != len(set(new_ids)):
        LOG.error('New ids may not be unique. Aborting.')
        quit(1)

    db.creator.truncate()

    for creator in creators:
        query = (db.creator_bak.id == creator.old_id)
        values = db(query).select().first().as_dict()
        values['id'] = creator.new_id
        db.creator.insert(**values)
        db.commit()
        creator.update_tables()

    drop_sql = """DROP TABLE creator_bak;"""
    db.executesql(drop_sql)
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
