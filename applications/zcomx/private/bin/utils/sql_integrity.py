#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sql_integrity.py

Compare the 'define_tables' table fields to actual table fields in sqlite db.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


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
        OR type = ?
        ORDER BY name
        ;
    """
    placeholders = ['table', 'view']
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
    print("""
OVERVIEW
    This script reports any inconsistencies in models and sqlite db tables.
    Reports:
    * Differences between the model tables and views vs actual sqlite db
      tables.
    * Differences between the model table fields vs actual sqlite db table
      columns.

USAGE
    sql_integrity.py [OPTIONS]

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

    parser = argparse.ArgumentParser(prog='sql_integrity.py')

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

    compare_tables()
    compare_fields()


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
