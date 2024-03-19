#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
create_sitemap.py
"""
import argparse
import sys
import traceback
from gluon import *
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import (
    generator,
    get_page,
    page_url,
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
    # (page, changefreq, priority, has_generator)
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
    for value in generator(query, as_url=as_url):
        yield value


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
OVERVIEW
    This script will create print sitemap XML for the zco.mx site.

USAGE
    create_sitemap.py
    create_sitemap.py -vv                         # Verbose output
    create_sitemap.py -o path/to/sitemap.xml       # Output to file

    --version
        Print the script version.

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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='create_sitemap.py')

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-o', '--out-file',
        dest='outfile', default=None,
        help='Write output to this file.',
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

    LOG.info('Started.')

    xml_version_line = '<?xml version="1.0" encoding="UTF-8"?>'
    sitemap = TAG.urlset(_xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for mapper in MAPPERS:
        page, changefreq, priority, has_generator = mapper
        if has_generator:
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

    xml_str = xml_version_line + "\n" + sitemap.xml().decode('utf-8')
    xml_str = xml_str.replace('</url>', '</url>\n')
    if args.outfile:
        with open(args.outfile, 'w') as f:
            f.write(xml_str)
    else:
        print(xml_str)

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
