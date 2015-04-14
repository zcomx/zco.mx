#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
post_book_on_tumblr.py

Script to post a book on tumblr.
"""
import logging
from gluon import *
from optparse import OptionParser
from applications.zcomx.modules.books import \
    tumblr_data as book_tumblr_data
from applications.zcomx.modules.creators import \
    tumblr_data as creator_tumblr_data
from applications.zcomx.modules.tumblr import \
    Authenticator, \
    PhotoDataPreparer, \
    Poster
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row
from applications.zcomx.modules.zco import SITE_NAME


VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    post_book_on_tumblr.py [OPTIONS] book_id               # Post book

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

    usage = '%prog [options] book_id'
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

    LOG.debug('Starting')
    book_id = args[0]

    book = entity_to_row(db.book, book_id)
    if not book:
        raise NotFoundError('Book not found, id: %s', book_id)

    creator = entity_to_row(db.creator, book.creator_id)
    if not creator:
        raise NotFoundError('Creator not found, id: %s', book.creator_id)

    LOG.debug('Creating tumblr posting for: %s', book.name)

    settings = current.app.local_settings
    credentials = {
        'consumer_key': settings.tumblr_consumer_key,
        'consumer_secret': settings.tumblr_consumer_secret,
        'oauth_token': settings.tumblr_oauth_token,
        'oauth_secret': settings.tumblr_oauth_secret,
    }
    client = Authenticator(credentials).authenticate()
    poster = Poster(client)
    tumblr_data = {
        'book': book_tumblr_data(book),
        'creator': creator_tumblr_data(creator),
        'site': {'name': SITE_NAME},
    }
    photo_data = PhotoDataPreparer(tumblr_data).data()
    if settings.tumblr_post_state:
        photo_data['state'] = settings.tumblr_post_state
    LOG.debug('photo_data: %s', photo_data)
    result = poster.post_photo(settings.tumblr_username, photo_data)
    if 'id' not in result:
        LOG.error(
            'Tumblr post failed for book: %s - %s', book.id, book.name
        )
        # Try to get an error message.
        if 'meta' in result:
            if 'status' in result['meta'] and 'msg' in result['meta']:
                LOG.error(
                    'Status: %s, msg: %s',
                    result['meta']['status'],
                    result['meta']['msg']
                )

        if 'response' in result and 'errors' in result['response']:
            for error in result['response']['errors']:
                LOG.error(error)
        quit(1)

    post_id = result['id']
    LOG.debug('post_id: %s', post_id)
    book.update_record(tumblr_post_id=post_id)
    db.commit()

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
