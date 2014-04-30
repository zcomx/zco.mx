#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
resize_images.py

Script to create and maintain images and their sizes.
"""
import datetime
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomix.modules.images import \
    SIZERS, \
    UploadImage, \
    set_thumb_dimensions

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')

FIELDS = [
    'creator.image',
    'book_page.image',
]


class ImageHandler(object):
    """Class representing a handler for image resizing."""

    def __init__(
            self,
            filenames,
            size=None,
            field=None,
            record_id=None,
            dry_run=False):
        """Constructor

        Args:
            filenames: list of image filenames, if empty all images are
                resized.
            size: string, one of SIZERS.keys()
            field: string, one of FIELDS
            record_id: integer, id of database record.
            dry_run: If True, make no changes.
        """
        self.filenames = filenames
        self.size = size
        self.field = field
        self.record_id = record_id
        self.dry_run = dry_run

    def image_generator(self):
        """Generator of images.

        Returns:
            tuple: (field, image_name, original image name)
        """
        fields = [self.field] if self.field else FIELDS
        for table_field in fields:
            table, field = table_field.split('.')
            db_field = db[table][field]
            db_table = db[table]
            query = (db_field)
            if self.record_id:
                query = (db_table.id == self.record_id)
            rows = db(query).select(db_table.id, db_field)
            for r in rows:
                try:
                    original_name, unused_fullname = db_field.retrieve(
                        r.image,
                        nameonly=True,
                    )
                except TypeError:
                    LOG.error('Image not found, {fld} {rid}:  {img}'.format(
                        fld=db_field, rid=r.id, img=r.image))
                    continue
                if self.filenames and original_name not in self.filenames:
                    continue
                yield (db_field, r.id, r.image, original_name)

    def purge(self):
        """Purge orphanned images."""
        LOG.warn('NOTICE: The purge feature is not implemented yet.')
        return

    def resize(self):
        """Resize images."""
        LOG.debug('{a}: {t} {i} {f} {s}'.format(
            a='Action', t='table', i='id', f='image', s='size'))
        sizes = [self.size] if self.size else SIZERS.keys()
        for field, record_id, image_name, original in self.image_generator():
            resizer = UploadImage(field, image_name)
            for size in sizes:
                action = 'Dry run' if self.dry_run else 'Resizing'
                LOG.debug('{a}: {t} {i} {f} {s}'.format(
                    a=action, t=field.table, i=record_id, f=original, s=size))
                if not self.dry_run:
                    try:
                        resizer.resize(size)
                    except IOError as err:
                        LOG.error('Unable to resize: {f} {i} {s} - {e}'.format(
                            f=field, i=record_id, s=size, e=err))
                        continue
                    if str(field) == 'book_page.image' and size == 'thumb':
                            set_thumb_dimensions(
                                db, record_id, resizer.dimensions(size='thumb')
                            )


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    resize_images.py [OPTIONS] [FILE...]

    # Create sizes for every image as necessary.
    resize_images.py

    # Create sizes for specific images.
    resize_images.py file.jpg file2.jpg

    # Create sizes for images associated with a specific field.
    resize_images.py --field creator.image

    # Create sizes for an image associated with a specific record.
    resize_images.py --field creator.image --id 123

    # Create medium sized images for all images as necessary.
    resize_images.py --size medium

    # Purge orphaned images and exit.
    resize_images.py --purge

OPTIONS
    -d, --dry-run
        Do not make any changes, only report what would be done.

    -f FIELD,  --field=FIELD
        Update only images associated with the database field FIELD. FIELD is
        of the format 'table.field'. Eg creator.image. Use --fields option
        to list available fields.

    --fields
        List all database image fields.

    -h, --help
        Print a brief help.

    -i ID, --id=ID
        Update a single image, the one associated with the database record with
        id ID. This option requires the --field option to indicate which
        database table the record is from.

    --man
        Print man page-like help.

    -p, --purge
        Delete orphaned images and exit. An orphaned image is a resized image
        where the original image it was based on no longer exists.

    -s SIZE, --size=SIZE
        By default, images are resized to each of the standard sizes. With
        this option, images are resized to SIZE only. Use --sizes option to
        list valid values for SIZE.

    --sizes
        List all available image sizes.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """


def main():
    """Main processing."""

    usage = '%prog [options] [file...]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not resize images. Only report what would be done.',
    )
    parser.add_option(
        '-f', '--field',
        choices=FIELDS,
        dest='field', default=None,
        help='Resize images associated with this database field: table.field',
    )
    parser.add_option(
        '--fields',
        action='store_true', dest='fields', default=False,
        help='List all database image fields and exit.',
    )
    parser.add_option(
        '-i', '--id',
        dest='id', default=None,
        help='Resize images associated with record with this id.',
    )
    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-p', '--purge',
        action='store_true', dest='purge', default=False,
        help='Purge orphaned images.',
    )
    parser.add_option(
        '-s', '--size',
        choices=SIZERS.keys(),
        dest='size', default=None,
        help='Resize images to this size only.',
    )
    parser.add_option(
        '--sizes',
        action='store_true', dest='sizes', default=False,
        help='List all available image sizes and exit.',
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

    quick_exit = False

    if options.fields:
        print 'Database image fields:'
        for f in FIELDS:
            print '    {f}'.format(f=f)
        quick_exit = True

    if options.sizes:
        print 'Image sizes:'
        for name, sizer_class in SIZERS.items():
            if hasattr(sizer_class, 'dimensions'):
                w, h = getattr(sizer_class, 'dimensions')
                print '    {n}: ({w} x {h})'.format(n=name, w=w, h=h)
            else:
                print '    {n}: (variable)'.format(n=name)
        quick_exit = True

    if quick_exit:
        exit(0)

    LOG.info('Started.')
    filenames = args or []

    handler = ImageHandler(
        filenames,
        size=options.size,
        field=options.field,
        record_id=options.id,
        dry_run=options.dry_run,
    )

    if options.purge:
        handler.purge()
    else:
        handler.resize()

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
