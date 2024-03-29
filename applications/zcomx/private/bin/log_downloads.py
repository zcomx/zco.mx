#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
log_downloads.py

Script to log download clicks.
"""
import argparse
import functools
import sys
import time
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.events import (
    Download,
    DownloadClick,
    DownloadEvent,
)
from applications.zcomx.modules.job_queuers import \
    LogDownloadsQueuer
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def log(download_click_id, book_id):
    """Log a download click

    Args:
        download_click_id: integer, id of download_click record
        book_id: integer, id of book record
    """
    click = DownloadClick.from_id(download_click_id)
    if not click:
        raise LookupError('download_click not found, id: {i}'.format(
            i=download_click_id))

    book = Book.from_id(book_id)
    return DownloadEvent(book, click.auth_user_id).log(value=click)


def rm_unloggables():
    """Remove download records associated with unloggable download_click
    records.
    """

    query = (db.download_click.loggable == False) & \
        (db.download_click.completed == False)

    rows = db(query).select(
        db.download.id,
        left=[
            db.download_click.on(
                db.download.download_click_id == db.download_click.id)
        ],
    )

    count = 0
    for r in rows:
        download = Download.from_id(r.id)
        LOG.debug(
            'Deleting download id %s for book id: %s',
            download.id,
            download.book_id
        )
        download.delete()
        # Prevent script from locking db
        count += 1
        if count % 10 == 0:
            time.sleep(1)


def unlogged_generator(limit=None):
    """Generator for unlogged download clicks.

    Args:
        limit: integer, limit to this number of records. If None, no limit.

    Returns:
        yields tuple: (download_click.id, book.id)
    """
    query = (db.download_click.loggable == True) & \
            (db.download_click.completed == False)
    click_ids = [x.id for x in db(query).select(
        db.download_click.id, orderby=db.download_click.id)]
    for download_click_id in click_ids:

        click = DownloadClick.from_id(download_click_id)
        if not click:
            raise LookupError('download_click not found, id: {i}'.format(
                i=download_click_id))

        queries = []
        queries.append((db.download_click.id == click.id))

        downloadable_query = (db.book.release_date != None) & \
            (db.book.fileshare_date != None)
        not_logged_query = (db.download.id == None)

        queries.append(downloadable_query)
        queries.append(not_logged_query)
        if click.record_table == 'all':
            pass
        elif click.record_table == 'creator':
            queries.append(db.book.creator_id == click.record_id)
        elif click.record_table == 'book':
            queries.append(db.book.id == click.record_id)
        else:
            raise SyntaxError(
                'Invalid download_click.record_table: {t}'.format(
                    t=click.record_table)
            )

        query = functools.reduce(lambda x, y: x & y, queries)
        limitby = (0, limit) if limit is not None else None

        rows = db(query).select(
            db.book.id,
            left=[
                db.download_click.on(
                    db.download_click.id == db.download.download_click_id),
                db.download.on(db.book.id == db.download.book_id),
            ],
            limitby=limitby
        )

        if rows:
            for r in rows:
                yield (click.id, r.id)
        else:
            query = (db.download_click.id == click.id)
            db(query).update(completed=True)
            db.commit()


def man_page():
    """Print manual page-like help"""
    print("""

USAGE
    log_downloads.py [OPTIONS]                 # Log all incompleted downloads
    log_downloads.py [OPTIONS] --limit 10      # Log a maximum of 10 downloads
    log_downloads.py [OPTIONS] -l 10 --requeue # Requeue the script if more
                                               # than 10 downloads need logging.

OPTIONS
    -h, --help
        Print a brief help.

    -l LIMIT, --limit=LIMIT
        Log a maximum of LIMIT download clicks and then exit.
        If LIMIT=0, all existing incomplete download clicks are logged.

    --man
        Print man page-like help.

    -r, --requeue
        If the --limit=LIMIT option is given and the number of incomplete
        downloads is greater than LIMIT, requeue the script to complete the
        remainder. The script will be requeued with the same options as
        called with.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='log_downloads.py')

    parser.add_argument(
        '-l', '--limit', type=int,
        dest='limit', default=0,
        help='Limit the number of download clicks logged.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-r', '--requeue',
        action='store_true', dest='requeue', default=False,
        help='Requeue the script if unlogged downloads remain.',
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

    LOG.debug('Starting')
    limit = args.limit if args.limit != 0 else None
    count = 0
    for click_id, book_id in unlogged_generator(limit=limit):
        log(click_id, book_id)
        count = count + 1
        if limit is not None and count >= limit:
            break
        if count % 10 == 0:
            time.sleep(1)

    rm_unloggables()

    sql = """
        UPDATE book SET downloads=(
            SELECT count(*) from download d WHERE d.book_id = book.id
        )
        ;
    """
    db.executesql(sql)

    requeue = False
    if args.requeue:
        try:
            next(unlogged_generator(limit=1))
        except StopIteration:
            requeue = False
        else:
            requeue = True
    if requeue:
        job = LogDownloadsQueuer(
            db.job,
            cli_options={'-r': requeue, '-l': str(args.limit)},
        ).queue()
        LOG.debug('Requeue job id: %s', job.id)

    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
