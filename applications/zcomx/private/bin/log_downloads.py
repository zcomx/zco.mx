#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
log_downloads.py

Script to log download clicks.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
from optparse import OptionParser
from applications.zcomx.modules.books import \
    Book, \
    DownloadEvent
from applications.zcomx.modules.job_queue import \
    LogDownloadsQueuer
from applications.zcomx.modules.utils import \
    entity_to_row

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def log(download_click_id, book_id):
    """Log a download click

    Args:
        download_click_id: integer, id of download_click record
        book_id: integer, id of book record
    """
    click = entity_to_row(db.download_click, download_click_id)
    if not click:
        raise LookupError('download_click not found, id: {i}'.format(
            i=download_click_id))

    book = Book.from_id(book_id)
    return DownloadEvent(book, click.auth_user_id).log(value=click)


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

        click = entity_to_row(db.download_click, download_click_id)
        if not click:
            raise LookupError('download_click not found, id: {i}'.format(
                i=download_click_id))

        queries = []
        queries.append((db.download_click.id == click.id))

        downloadable_query = (db.book.release_date != None) & \
            (db.book.torrent != None)
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

        query = reduce(lambda x, y: x & y, queries) if queries else None
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
            click.update_record(completed=True)
            db.commit()


def man_page():
    """Print manual page-like help"""
    print """

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

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-l', '--limit', type='int',
        dest='limit', default=0,
        help='Limit the number of download clicks logged.',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-r', '--requeue',
        action='store_true', dest='requeue', default=False,
        help='Requeue the script if unlogged downloads remain.',
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

    LOG.debug('Starting')
    limit = options.limit if options.limit != 0 else None
    count = 0
    for click_id, book_id in unlogged_generator(limit=limit):
        log(click_id, book_id)
        count = count + 1
        if limit is not None and count >= limit:
            break

    sql = """
        UPDATE book SET downloads=(
            SELECT count(*) from download d WHERE d.book_id = book.id
        )
        ;
    """
    db.executesql(sql)

    requeue = False
    if options.requeue:
        try:
            unlogged_generator(limit=1).next()
        except StopIteration:
            requeue = False
        else:
            requeue = True
    if requeue:
        job = LogDownloadsQueuer(
            db.job,
            cli_options={'-r': requeue, '-l': str(options.limit)},
        ).queue()
        LOG.debug('Requeue job id: %s', job.id)


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
