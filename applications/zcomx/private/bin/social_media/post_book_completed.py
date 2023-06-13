#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
post_book_completed.py

Script to post a completed book on social media (eg facebook, tumblr and
twitter).
"""
import argparse
import sys
import traceback
from gluon import *
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.social_media import (
    SocialMediaPostError,
    SocialMediaPoster,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    post_book_completed.py [OPTIONS] book_id               # Post book

OPTIONS
    -f, --force
        Post regardless if book record indicates a post has already been
        made (ie book.tumblr_post_id and book.twitter_post_id are set)

    --facebook
        Post only on facebook.

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    --tumblr
        Post only on tumblr.

    --twitter
        Post only on twitter.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='post_book_completed.py')

    parser.add_argument('book_id', type=int)

    parser.add_argument(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Post regardles if book post_ids exist.',
    )
    parser.add_argument(
        '--facebook',
        action='store_true', dest='facebook', default=False,
        help='Post only on facebook.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '--tumblr',
        action='store_true', dest='tumblr', default=False,
        help='Post only on tumblr.',
    )
    parser.add_argument(
        '--twitter',
        action='store_true', dest='twitter', default=False,
        help='Post only on twitter.',
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
    book_id = args.book_id

    book = Book.from_id(book_id)
    creator = Creator.from_id(book.creator_id)

    services = []
    if args.facebook:
        services.append('facebook')
    if args.tumblr:
        services.append('tumblr')
    if args.twitter:
        services.append('twitter')
    if not args.facebook and not args.tumblr and not args.twitter:
        services = ['facebook', 'tumblr', 'twitter']

    inactive_services = ['facebook']

    for social_media_service in services:
        if social_media_service in inactive_services:
            LOG.info('Posting discontinued for: %s', social_media_service)
            continue

        LOG.debug('Posting to: %s', social_media_service)
        poster = SocialMediaPoster.class_factory(social_media_service)
        try:
            post_id = poster.post(book, creator)
        except SocialMediaPostError as err:
            post_id = None
            LOG.error(
                'Social media post (%s) failed for book: %s - %s',
                social_media_service,
                book.id,
                book.name
            )
            if err:
                LOG.error(err)

        if post_id:
            field = '{s}_post_id'.format(s=social_media_service)
            data = {field: post_id}
            book = Book.from_updated(book, data)

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
