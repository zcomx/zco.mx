#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
cc_licences.py

Script to create cc_licence records. Script can be re-run without creating
duplicate records, but will update/replace existing records.
"""
import logging
import os
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomx.modules.utils import NotFoundError

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')

# line-too-long (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301

# The TEMPLATES elements are matched to cc_licence db records on the 'number'
# field. Changing 'number' values may result in data corruption.
TEMPLATES = [
    {
        'number': 0,
        'code': 'CC0',
        'url': 'http://creativecommons.org/publicdomain/zero/1.0',
        'template_img': """TO THE EXTENT POSSIBLE UNDER LAW, {owner} HAS WAIVED ALL COPYRIGHT AND RELATED OR NEIGHBORING RIGHTS TO "{title}".  THIS WORK IS PUBLISHED FROM: {place}.  FOR MORE INFORMATION, VISIT {url}.""",
        'template_web': """TO THE EXTENT POSSIBLE UNDER LAW, <a href="{owner_url}">{owner}</a> HAS <a href="{url}" target="_blank">WAIVED ALL COPYRIGHT AND RELATED OR NEIGHBORING RIGHTS</a> TO <a href="{title_url}">{title}</a>.&nbsp; THIS WORK IS PUBLISHED FROM: {place}."""
    },
    {
        'number': 1,
        'code': 'CC BY',
        'url': 'http://creativecommons.org/licenses/by/4.0',
        'template_img': """ "{title}" IS COPYRIGHT (C) {year} BY {owner}.  THIS WORK IS LICENSED UNDER THE CREATIVE COMMONS ATTRIBUTION 4.0 INTERNATIONAL LICENSE. TO VIEW A COPY OF THIS LICENSE, VISIT {url}.""",
        'template_web': """<a href="{title_url}">{title}</a>&nbsp; IS COPYRIGHT (C) {year} BY <a href="{owner_url}">{owner}</a>.&nbsp; THIS WORK IS LICENSED UNDER THE <a href="{url}" target="_blank">CC BY 4.0 INT`L LICENSE</a>."""
    },
    {
        'number': 2,
        'code': 'CC BY-ND',
        'url': 'http://creativecommons.org/licenses/by-nd/4.0',
        'template_img': """ "{title}" IS COPYRIGHT (C) {year} BY {owner}.  THIS WORK IS LICENSED UNDER THE CREATIVE COMMONS ATTRIBUTION-NODERIVATIVES 4.0 INTERNATIONAL LICENSE. TO VIEW A COPY OF THIS LICENSE, VISIT {url}.""",
        'template_web': """<a href="{title_url}">{title}</a>&nbsp; IS COPYRIGHT (C) {year} BY <a href="{owner_url}">{owner}</a>.&nbsp; THIS WORK IS LICENSED UNDER THE <a href="{url}" target="_blank">CC BY-ND 4.0 INT`L LICENSE</a>."""
    },
    {
        'number': 3,
        'code': 'CC BY-SA',
        'url': 'http://creativecommons.org/licenses/by-sa/4.0',
        'template_img': """ "{title}" IS COPYRIGHT (C) {year} BY {owner}.  THIS WORK IS LICENSED UNDER THE CREATIVE COMMONS ATTRIBUTION-SHAREALIKE 4.0 INTERNATIONAL LICENSE. TO VIEW A COPY OF THIS LICENSE, VISIT {url}.""",
        'template_web': """<a href="{title_url}">{title}</a>&nbsp; IS COPYRIGHT (C) {year} BY <a href="{owner_url}">{owner}</a>.&nbsp; THIS WORK IS LICENSED UNDER THE <a href="{url}" target="_blank">CC BY-SA 4.0 INT`L LICENSE</a>."""
    },
    {
        'number': 4,
        'code': 'CC BY-NC',
        'url': 'http://creativecommons.org/licenses/by-nc/4.0',
        'template_img': """ "{title}" IS COPYRIGHT (C) {year} BY {owner}.  THIS WORK IS LICENSED UNDER THE CREATIVE COMMONS ATTRIBUTION-NONCOMMERCIAL 4.0 INTERNATIONAL LICENSE. TO VIEW A COPY OF THIS LICENSE, VISIT {url}.""",
        'template_web': """<a href="{title_url}">{title}</a>&nbsp; IS COPYRIGHT (C) {year} BY <a href="{owner_url}">{owner}</a>.&nbsp; THIS WORK IS LICENSED UNDER THE <a href="{url}" target="_blank">CC BY-NC 4.0 INT`L LICENSE</a>."""
    },
    {
        'number': 5,
        'code': 'CC BY-NC-ND',
        'url': 'http://creativecommons.org/licenses/by-nc-nd/4.0',
        'template_img': """ "{title}" IS COPYRIGHT (C) {year} BY {owner}.  THIS WORK IS LICENSED UNDER THE CREATIVE COMMONS ATTRIBUTION-NONCOMMERCIAL-NODERIVATIVES 4.0 INTERNATIONAL LICENSE. TO VIEW A COPY OF THIS LICENSE, VISIT {url}.""",
        'template_web': """<a href="{title_url}">{title}</a>&nbsp; IS COPYRIGHT (C) {year} BY <a href="{owner_url}">{owner}</a>.&nbsp; THIS WORK IS LICENSED UNDER THE <a href="{url}" target="_blank">CC BY-NC-ND 4.0 INT`L LICENSE</a>."""
    },
    {
        'number': 6,
        'code': 'CC BY-NC-SA',
        'url': 'http://creativecommons.org/licenses/by-nc-sa/4.0',
        'template_img': """ "{title}" IS COPYRIGHT (C) {year} BY {owner}.  THIS WORK IS LICENSED UNDER THE CREATIVE COMMONS ATTRIBUTION-NONCOMMERCIAL-SHAREALIKE 4.0 INTERNATIONAL LICENSE. TO VIEW A COPY OF THIS LICENSE, VISIT {url}.""",
        'template_web': """<a href="{title_url}">{title}</a>&nbsp; IS COPYRIGHT (C) {year} BY <a href="{owner_url}">{owner}</a>.&nbsp; THIS WORK IS LICENSED UNDER THE <a href="{url}" target="_blank">CC BY-NC-SA 4.0 INT`L LICENSE</a>."""
    },
    {
        'number': 7,
        'code': 'All Rights Reserved',
        'url': '',
        'template_img': """ "{title}" IS COPYRIGHT (C) {year} BY {owner}.  ALL RIGHTS RESERVED.  PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR.""",
        'template_web': """<a href="{title_url}">{title}</a>&nbsp; IS COPYRIGHT (C) {year} BY <a href="{owner_url}">{owner}</a>.&nbsp; ALL RIGHTS RESERVED.&nbsp; PERMISSION TO REPRODUCE CONTENT MUST BE OBTAINED FROM THE AUTHOR."""
    },
]


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    cc_licences.py [OPTIONS]


OPTIONS
    -c, --clear
        Truncate the cc_licence table before updating table. Warning:
        cc_licence records are referenced by other tables. Truncating may
        corrupt data.

    -d, --dry-run
        Do not create licence records, only report what would be done.

    -h, --help
        Print a brief help.

    --man
        Print extended help.

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
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Truncate cc_licence table.',
    )
    parser.add_option(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not create licences. Report what would be done.',
    )
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

    if options.clear:
        LOG.debug('Truncating cc_licence table.')
        if not options.dry_run:
            db.cc_licence.truncate()
            db.commit()
        else:
            LOG.debug('Dry run. No changes made.')

    LOG.info('Started.')

    for template_dict in TEMPLATES:
        template = Storage(template_dict)
        cc_licence = db(db.cc_licence.number == template.number).select().first()
        if cc_licence:
            LOG.debug('Updating: %s', template.number)
        else:
            LOG.debug('Adding: %s', template.number)
            if not options.dry_run:
                db.cc_licence.insert(number=template.number)
                db.commit()
                cc_licence = db(db.cc_licence.number == template.number).select().first()
        if not cc_licence:
            raise NotFoundError('cc_licence not found, number: {number}'.format(
                number=template.number))
        if not options.dry_run:
            cc_licence.update_record(
                code=template.code,
                url=template.url,
                template_img=template.template_img,
                template_web=template.template_web
            )
            db.commit()
        else:
            LOG.debug('Dry run. No changes made.')

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
