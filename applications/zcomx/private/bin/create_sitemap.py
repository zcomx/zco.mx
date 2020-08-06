#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
create_sitemap.py

Script to tally the yearly and monthly contributions, ratings, and views for
each book.
"""

import sys
import traceback
from optparse import OptionParser
from gluon import *
from applications.zcomx.modules.books import (
    Book,
    get_page,
    page_url,
    url as book_url,
)
from applications.zcomx.modules.creators import (
    Creator,
    url as creator_url,
)
from applications.zcomx.modules.logger import set_cli_logging
from applications.zcomx.modules.sitemap import SiteMapUrl
from applications.zcomx.modules.zco import BOOK_STATUS_ACTIVE

VERSION = 'Version 0.1'

MAPPERS = [
    # (page, changefreq, priority, generator)
    ('book', 'monthly', 1.0, True),
    ('cover_page', 'monthly', 1.0, True),
    ('creator', 'monthly', 1.0, True),
    ('completed', 'daily', 1.0, False),
    ('ongoing', 'daily', 1.0, False),
    ('cartoonist', 'daily', 1.0, False),
    ('about', 'yearly', 0.2, False),
    ('copyright_claim', 'yearly', 0.2, False),
    ('expenses', 'yearly', 0.2, False),
    ('faq', 'yearly', 0.2, False),
    ('logos', 'yearly', 0.2, False),
    ('overview', 'yearly', 0.2, False),
    ('terms', 'yearly', 0.2, False),
]


def book_generator(as_url=True):
    """Generator of book sitemap urls.

    Args:
        as_url: If True return the book url, else return the Book instance

    Returns:
        str or Book instance
    """
    query = (db.book.status == BOOK_STATUS_ACTIVE)
    for book_id in db(query).select(db.book.id):
        book = Book.from_id(book_id)
        if not book:
            continue
        if as_url:
            yield book_url(book)
        else:
            yield book


def cover_page_generator():
    """Generator of cover page sitemap urls."""
    for book in book_generator(as_url=False):
        first_page = get_page(book, page_no='first')
        yield page_url(first_page)


def creator_generator():
    """Generator of creator sitemap urls."""
    query = (db.book.status == BOOK_STATUS_ACTIVE)
    creator_ids = db(query).select(
        db.creator.id,
        left=[
            db.creator.on(db.book.creator_id == db.creator.id),
        ],
        groupby=db.creator.id
    )

    for creator_id in creator_ids:
        creator = Creator.from_id(creator_id)
        if not creator:
            continue
        yield creator_url(creator)


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    create_sitemap.py
    create_sitemap.py --vv                         # Verbose output
    create_sitemap.py -o path/to/sitemap.xml       # Output to file

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -o FILE, --out-file=FILE
        By default sitemap is printed to stdout. With this option, the
        output is written to file FILE.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """)


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
        '-o', '--out-file',
        dest='outfile', default=None,
        help='Write output to this file.',
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

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.info('Started.')
    sitemap = TAG.urlset(_xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for mapper in MAPPERS:
        page, changefreq, priority, generator = mapper
        if generator:
            generator_func = '{p}_generator'.format(p=page)
            for relative_url in globals()[generator_func]():
                url = '{w}{u}'.format(
                    w=local_settings.web_site_url, u=relative_url)
                sitemap.append(
                    SiteMapUrl(
                        url,
                        changefreq=changefreq,
                        priority=priority
                    ).xml_component()
                )
        else:
            url = '{w}/z/{p}'.format(w=local_settings.web_site_url, p=page)
            sitemap.append(
                SiteMapUrl(
                    url,
                    changefreq=changefreq,
                    priority=priority
                ).xml_component()
            )

    if options.outfile:
        with open(options.outfile, 'wb') as f:
            f.write(sitemap.xml())
    else:
        print(sitemap.xml())

    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
