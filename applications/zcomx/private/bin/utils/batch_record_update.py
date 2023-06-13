#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
batch_record_update.py

Script to update records from data read from csv file.
"""
import argparse
import collections
import csv
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging
from applications.zcomx.modules.records import Record

VERSION = 'Version 0.1'


MAX_ERRORS = 10
CSV_FIELDS = [
    'table',
    'key_field',
    'key_value',
    'field',
    'value',
]

ADDED = 'Added'
INVALID = 'Invalid'
UNCHANGED = 'Unchanged'
UPDATED = 'Updated'


class TableRecord(Record):
    """Class representing a record with table not yet known."""
    db_table = None


class BatchUpdaterRecord():
    """Class representing a batch updater record"""

    def __init__(self, record, dry_run=False):
        """Constructor

        Args:
            record: string, first arg
            dry_run: If True, do not update database records
        """
        self.record = record
        self.dry_run = dry_run
        self.action = UNCHANGED
        self.stats = collections.OrderedDict({
            ADDED: 0,
            UPDATED: 0,
            UNCHANGED: 0,
            INVALID: 0,
        })

    def update(self):
        """Update the record"""
        if self.dry_run:
            LOG.debug('Dry run, record not updated')
            self.action = UNCHANGED
            return

        values = {}
        for field in CSV_FIELDS:
            try:
                values[field] = self.record[CSV_FIELDS.index(field)]
            except (KeyError, ValueError):
                msg = 'Incorrect fields: {rec}'.format(rec=self.record)
                LOG.error(msg)
                self.action = INVALID
                return

        TableRecord.db_table = values['table']
        key = {values['key_field']: values['key_value']}
        try:
            record = TableRecord.from_key(key)
        except LookupError as err:
            LOG.error(err)
            self.action = INVALID
            return

        if str(record[values['field']]) != values['value']:
            data = {values['field']: values['value']}
            try:
                record = TableRecord.from_updated(record, data)
            except SyntaxError as err:
                LOG.error(err)
                self.action = INVALID
                return

            self.action = UPDATED
        else:
            self.action = UNCHANGED
        return

    def valid(self):
        """Check of the record id valid.

        Returns:
            True if valid, False otherwise
        """
        # pylint: disable=too-many-return-statements
        if len(self.record) != len(CSV_FIELDS):
            msg = 'Incorrect number of fields: {rec}'.format(rec=self.record)
            LOG.error(msg)
            return False

        values = {}
        for field in CSV_FIELDS:
            try:
                values[field] = self.record[CSV_FIELDS.index(field)]
            except (KeyError, ValueError):
                msg = 'Incorrect fields: {rec}'.format(rec=self.record)
                LOG.error(msg)
                return False

        # Test table
        if values['table'] not in db:
            LOG.error('Invalid table: %s', values['table'])
            return False

        # Test key_field
        if values['key_field'] not in db[values['table']].fields:
            LOG.error(
                'Invalid key field: %s.%s',
                values['table'],
                values['key_field']
            )
            return False

        TableRecord.db_table = values['table']
        key = {values['key_field']: values['key_value']}
        try:
            TableRecord.from_key(key)
        except LookupError as err:
            LOG.error(err)
            return False

        # Test field
        if values['field'] not in db[values['table']].fields:
            LOG.error(
                'Invalid field: %s.%s',
                values['table'],
                values['field']
            )
            return False

        return True


class BatchUpdater():
    """Class representing a batch updater"""

    def __init__(self, csv_filename, dry_run=False):
        """Constructor

        Args:
            csv_filename: string, first arg
            dry_run: If True, do not update database records
        """
        self.csv_filename = csv_filename
        self.dry_run = dry_run
        self.stats = collections.OrderedDict({
            ADDED: 0,
            UPDATED: 0,
            UNCHANGED: 0,
            INVALID: 0,
        })

    def generator(self):
        """Generator yielding CSV file records

        Yields:
            list, CSV file record
        """
        header_labels = ['table']
        seen_header = False
        with open(self.csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for record in reader:
                if not seen_header and record[0] in header_labels:
                    # Ignore header record
                    msg = 'Ignoring header record: {rec}'.format(rec=record)
                    LOG.debug(msg)
                    seen_header = True
                    continue
                yield BatchUpdaterRecord(record, dry_run=self.dry_run)

    def set_invalid(self, max_errors=MAX_ERRORS):
        """Validate all records

        Args:
            max_errors: integer, maximum number of errors before aborting
        """
        self.stats[INVALID] = 0
        for record in self.generator():
            if self.stats[INVALID] >= max_errors:
                return
            if not record.valid():
                self.stats[INVALID] += 1

    def update(self):
        """Update for all records

        Returns:
            Number of records imported.
        """
        for record in self.generator():
            record.update()
            self.stats[record.action] += 1

    def valid_csv_filename(self):
        """Test if csv filename is valid.

        Returns:
            True if CSV file exists and is readible, False other wise.
        """
        try:
            next(self.generator())
        except IOError as err:
            msg = 'Invalid CSV file: {file}'.format(file=self.csv_filename)
            LOG.error(msg)
            LOG.error(err)
            return False
        return True


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    batch_record_update.py [OPTIONS] file.csv

FORMAT
    The format of the file.csv should be:

        table,key_field,key_value,field,value

    Example csv records

    # Update the name of a book with id=123 to 'My Title'
        book,id,123,name,My Title

    # Update the publisher of a book with id=123 to 'Acme Inc'
        publication_metadata,book_id,123,publisher,Acme Inc

OPTIONS

    -d, --dry-run
        With this option, accessories are not updated to the database. This option
        is useful for validating the records in the CSV file without updating.

    -e INT, --errors=INT
        If this option is provided, the script will abort once the number
        of records with invalid data encountered reaches INT.

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

    parser = argparse.ArgumentParser(prog='batch_record_update.py')

    parser.add_argument('csv_filename')

    parser.add_argument(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. File validated. No accessories changed.',
    )
    parser.add_argument(
        '-e', '--errors', type=int,
        dest='max_errors', default=MAX_ERRORS,
        help='Maximum number of errors before aborting.',
    )
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

    csv_filename = args.csv_filename

    LOG.info('Started.')
    updater = BatchUpdater(csv_filename, dry_run=args.dry_run)
    if updater.valid_csv_filename():
        LOG.info('Validating data.')
        updater.set_invalid(max_errors=args.max_errors)
        if updater.stats[INVALID] == 0:
            LOG.info('Updating records.')
            LOG.info('Only changes are logged.')
            updater.update()
        else:
            LOG.error("Data is not valid. Aborting. No records updated.")

        total = 0
        for k, v in list(updater.stats.items()):
            total += v
            LOG.info('{k}: {v}'.format(k=k, v=v))
        LOG.info('TOTAL: {v}'.format(v=total))
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
