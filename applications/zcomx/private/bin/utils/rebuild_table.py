#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
rebuild_table.py

A script to rebuild db tables.
"""

import os
import sys
import tarfile
import tempfile
import traceback
from optparse import OptionParser
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


class RebuildError(Exception):
    """Exception class for rebuild errors."""
    pass


def backup():
    """Backup databases directory into a tarball.

    Returns:
        string, name of tarball
    """
    temp = tempfile.mkstemp(suffix='.tgz', prefix='databases_')
    if not temp or len(temp) < 2:
        raise RebuildError('Unable to create tempfile.')
    out = temp[1]

    source_dir = os.path.join(request.folder, 'databases')
    if not os.path.exists(source_dir):
        raise RebuildError('Not found: {d}'.format(d=source_dir))
    with tarfile.open(out, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    LOG.debug('Backup: %s', out)
    return out


def rebuild_table(tablename):
    """Rebuild a table.

    Args:
        tablename: string, name of db table.
    """
    LOG.debug('Rebuilding: %s', tablename)
    if tablename not in db:
        raise RebuildError('Table not found: {t}'.format(t=tablename))

    t_bak = '__'.join([tablename, 'bak'])

    if t_bak in db.tables:
        raise RebuildError(
            'Unable to create temp table. Already exists. {t}'.format(
                t=t_bak)
        )

    dbt = '{t}.table'.format(t=t_bak)
    db.define_table(t_bak, db[tablename], migrate=dbt)

    fields_str = ','.join(db[tablename].fields)
    db[t_bak].truncate()
    db.commit()

    sql = """
        INSERT INTO {t_bak} SELECT {fields} FROM {t};
    """.format(
        fields=fields_str,
        t=tablename,
        t_bak=t_bak,
    )
    db.executesql(sql)
    count = db(db[tablename]).count()
    count_bak = db(db[t_bak]).count()
    if count != count_bak:
        msg = (
            'Mismatch record count. Aborting.'
            ' {t}: {c} records,'
            ' {t_bak}: {c_bak} records'
        ).format(t=tablename, c=str(count), t_bak=t_bak, c_bak=str(count_bak))
        raise RebuildError(msg)

    sql = """
        DROP TABLE {t};
    """.format(t=tablename)
    db.executesql(sql)

    sql = """
        ALTER TABLE {t_bak} RENAME TO {t};
    """.format(
        t=tablename,
        t_bak=t_bak,
    )
    db.executesql(sql)

    # Rebuild the .table file.
    # pylint: disable=W0212
    # W0212: *Access to a protected member %%s of a client class*
    db._adapter.create_table(db[tablename], migrate=True, fake_migrate=True)
    db.commit()

    # Check record count. This also tests that we can access the table.
    count_new = db(db[tablename]).count()
    if count != count_new:
        msg = (
            'Mismatch record count. Status of table unknown.'
            ' {t} before: {c} records, '
            ' {t}  after: {c_new} records'
        ).format(t=tablename, c=str(count), c_new=str(count_new))
        raise RebuildError(msg)

    dbt_filename = os.path.join(db._adapter.folder, dbt)
    if os.path.exists(dbt_filename):
        os.unlink(dbt_filename)


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    Sqlite has some quirks and limitations.
    * No DROP COLUMN
    * ADD COLUMN appends fields to end. Tables on different servers
      can have fields in different order. Import from csv can fail.

    This script rebuild a db table so the columns match the model in name
    and in order.

USAGE
    rebuild_table.py [OPTIONS] table [table2 table3 ...]

EXAMPLE
    rebuild_table.py book
    rebuild_table.py book book_page creator

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

    usage = '%prog [options] table [table2 table3 ...]'
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

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) < 1:
        parser.print_help()
        exit(1)

    backup()

    for tablename in args:
        try:
            rebuild_table(tablename)
        except RebuildError as err:
            LOG.error(err)
            exit(1)

if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
