#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
optimize_img.py

Script to optimize an image.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
import os
from optparse import OptionParser
from applications.zcomx.modules.images import \
    SIZES, \
    UploadImage, \
    is_optimized, \
    optimize, \
    queue_optimize
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def run_optimize(field, record_id, options):
    """Optimize a field record.
    Args:
        field: gluon.dal.Field instance, eg db.creator.image
        record_id: integer, id of record
        options: dict, OptionParser options
    """
    if not options.force and is_optimized(str(field), record_id):
        LOG.debug(
            'Not necessary, already optimized: %s, id: %s', field, record_id)
        return

    record = entity_to_row(field.table, record_id)
    if not record:
        raise NotFoundError('Not found, field: {f}, id: {i}'.format(
            f=field, i=record_id))
    upload_image = UploadImage(field, record[field])
    up_folder = field.uploadfolder.rstrip('/').rstrip('original')

    LOG.debug('Optimizing: %s, id: %s', field, record_id)

    for size in SIZES:
        fullname = upload_image.fullname(size=size)
        if options.uploads and fullname.startswith(up_folder):
            filename = os.path.join(
                options.uploads,
                fullname.replace(up_folder, '', 1)
            )
        else:
            filename = fullname

        if os.path.exists(os.path.abspath(filename)):
            LOG.debug('Optimizing filename: %s', filename)
            optimize(filename, nice=True)

    db.optimize_img_log.insert(
        record_field=str(field),
        record_id=record_id
    )


def queue(field, record_id, options):
    """Queue the optimize of a field record."""
    cli_options = {}
    if options.force:
        cli_options['--force'] = True
    if options.priority:
        cli_options['--priority'] = options.priority
    queue_optimize(
        field,
        record_id,
        priority=options.priority,
        cli_options=cli_options,
    )


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    optimize_img.py [OPTIONS]                       # optimize all images
    optimize_img.py [OPTIONS] book_page.image       # optimize book_page images
    optimize_img.py [OPTIONS] book_page.image 123   # optimize single book page

OPTIONS
    -f, --force
        By default, if the image(s) associated with the field(s) have already
        been optimized, (indicated by a optimize_img_log record), the optimize
        is not run. With the --force option, it is optimized regardless.

    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -p PRIORITY --priority=PRIORITY
        Queue jobs at this priority. Must be one of PRIORITIES.
        Default 'optimize_img'.

    -u PATH --uploads-path=PATH
        Use this option to indicate the path of the directory the upload images
        are stored in. Default: application/zcomx/uploads

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] [field [record_id]]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Force optimize regardless of optimize_img_log record.',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-p', '--priority',
        dest='priority', default='optimize_img',
        help='Queue jobs at this priority.',
    )
    parser.add_option(
        '-u', '--uploads-path',
        dest='uploads', default=None,
        help='Path of directory upload images are stored in.',
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

    if len(args) > 2:
        print parser.print_help()
        quit(1)

    record_field = None
    record_id = None

    if len(args) == 1:
        record_field = args[0]
    elif len(args) == 2:
        record_field = args[0]
        record_id = args[1]

    LOG.debug('Starting')

    fields = []
    if record_field:
        fields = [record_field]
    else:
        for table in db.tables:
            for field in db[table].fields:
                if db[table][field].type == 'upload':
                    fields.append(str(db[table][field]))

    for fieldname in fields:
        try:
            table, field = fieldname.split('.', 1)
        except (AttributeError, ValueError):
            raise NotFoundError('Invalid field: {f}'.format(f=fieldname))
        if table not in db:
            raise NotFoundError('Invalid table: {t}'.format(t=table))
        if field not in db[table]:
            raise NotFoundError('Invalid field: {f}'.format(f=fieldname))
        if record_id:
            LOG.debug(
                'Run optimization on field: %s, id: %s', fieldname, record_id)
            run_optimize(db[table][field], record_id, options)
        else:
            ids = [x.id for x in db(db[table]).select(db[table].id)]
            for record_id in ids:
                LOG.debug('Queuing field: %s, id: %s', fieldname, record_id)
                queue(fieldname, record_id, options)

    LOG.debug('Done')


if __name__ == '__main__':
    main()
