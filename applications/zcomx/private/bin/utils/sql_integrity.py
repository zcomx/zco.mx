#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
sql_integrity.py

Compare the 'define_tables' table fields to actual table fields in sqlite db.
"""
import logging
from optparse import OptionParser

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def compare_fields():
    """Report differences in table fields found in db.tables and actual tables
    in sqlite.
    """
    for table in db.tables:
        sqlite_fields = []
        sql = """
            PRAGMA table_info({t})
            ;
        """.format(t=table)
        rows = db.executesql(sql)
        for r in rows:
            # Typical r
            # (id, name, data type, NULL, default, primary_key)
            # (0, u'id', u'INTEGER', 0, None, 1)
            sqlite_fields.append(r[1])

        msg = 'Field in define_tables, not in sqlite: %s'
        for field in set(db[table].fields).difference(set(sqlite_fields)):
            LOG.error(msg, '{t}.{f}'.format(t=table, f=field))

        msg = 'Field in sqlite, not in define_tables: %s'
        for field in set(sqlite_fields).difference(set(db[table].fields)):
            LOG.error(msg, '{t}.{f}'.format(t=table, f=field))


def compare_tables():
    """Report differences in tables found in db.tables and actual tables
    in sqlite.
    """
    sqlite_tables = []
    sql = """
        SELECT name
        FROM sqlite_master
        WHERE type = ?
        ORDER BY name
        ;
    """
    placeholders = ['table']
    rows = db.executesql(sql, placeholders=placeholders)
    for r in rows:
        sqlite_tables.append(r[0])

    msg = 'Table in define_tables, not in sqlite: %s'
    for table in set(db.tables).difference(set(sqlite_tables)):
        LOG.error(msg, table)

    ignore = ['test__reorder', 'sqlite_sequence']
    msg = 'Table in sqlite, not in define_tables: %s'
    for table in set(sqlite_tables).difference(set(db.tables)):
        if table in ignore:
            continue
        LOG.error(msg, table)


def man_page():
    """Print manual page-like help"""
    print """
OVERVIEW
    Sqlite has some quirks and limitations.
    * No DROP COLUMN
    * ADD COLUMN appends fields to end. Tables on different servers
      can have fields in different order. Import from csv can fail.

    This script rebuild a db table so the columns match the model in name
    and in order.

USAGE
    sql_integrity.py [OPTIONS]

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

    compare_tables()
    compare_fields()


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
