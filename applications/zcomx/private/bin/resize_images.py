#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
resize_images.py

Script to create and maintain images and their sizes.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
import traceback
from pydal.helpers.regex import REGEX_UPLOAD_PATTERN
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.images import \
    SIZES, \
    UploadImage, \
    store
from applications.zcomx.modules.shell_utils import \
    temp_directory
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']

FIELDS = [
    'creator.image',
    'book_page.image',
]


class ImageHandler():
    """Class representing a handler for image resizing."""

    def __init__(
            self,
            filenames,
            field=None,
            record_id=None,
            dry_run=False):
        """Constructor

        Args:
            filenames: list of image filenames, if empty all images are
                resized.
            field: string, one of FIELDS
            record_id: integer, id of database record.
            dry_run: If True, make no changes.
        """
        self.filenames = filenames
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
        original_dir = db.book_page.image.uploadfolder
        for unused_root, unused_dirs, files in os.walk(original_dir):
            for filename in files:
                # Eg creator.image.ac95985a97d9910d.66696c652e6a7067.jpg
                m = REGEX_UPLOAD_PATTERN.match(filename)
                table = m.group('table')
                field = m.group('field')
                query = (db[table][field] == filename)
                r = db(query).select(db[table].id).first()
                if not r:
                    action = 'Dry run' if self.dry_run else 'Deleting'
                    LOG.debug('{a}: {f}'.format(a=action, f=filename))
                    if not self.dry_run:
                        db_field = db[table][field]
                        up_image = UploadImage(db_field, filename)
                        up_image.delete_all()

    def resize(self):
        """Resize images."""
        LOG.debug('{a}: {t} {i} {f}'.format(
            a='Action', t='table', i='id', f='image'))
        for field, record_id, image_name, original in self.image_generator():
            action = 'Dry run' if self.dry_run else 'Resizing'
            LOG.debug('{a}: {t} {i} {f}'.format(
                a=action, t=field.table, i=record_id, f=original))
            up_image = UploadImage(field, image_name)
            src_filename = os.path.abspath(up_image.fullname())
            if not os.path.exists(src_filename):
                LOG.error('File not found: {fn}'.format(fn=src_filename))
                continue
            if self.dry_run:
                continue
            tmp_dir = temp_directory()
            filename = os.path.join(tmp_dir, original)
            shutil.copy(src_filename, filename)
            # Back up the 'original' so it can be restored on error.
            backup = '{f}.bak'.format(f=filename)
            shutil.copy(src_filename, backup)
            up_image = UploadImage(field, image_name)
            up_image.delete_all()
            try:
                stored_filename = store(field, filename)
            except Exception as err:
                if not os.path.exists(src_filename):
                    # Restore the file so it is not lost.
                    shutil.copy(backup, src_filename)
                raise err
            data = {field.name: stored_filename}
            db(field.table.id == record_id).update(**data)
            db.commit()
            if tmp_dir:
                shutil.rmtree(tmp_dir)


def man_page():
    """Print manual page-like help"""
    print("""
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

    --sizes
        List all available image sizes.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.

    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='resize_images.py')

    parser.add_argument(
        'filenames',
        nargs='*',
        default=[],
        metavar='filename [filename ...]',
    )

    parser.add_argument(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not resize images. Only report what would be done.',
    )
    parser.add_argument(
        '-f', '--field',
        choices=FIELDS,
        dest='field', default=None,
        help='Resize images associated with this database field: table.field',
    )
    parser.add_argument(
        '--fields',
        action='store_true', dest='fields', default=False,
        help='List all database image fields and exit.',
    )
    parser.add_argument(
        '-i', '--id',
        dest='id', default=None,
        help='Resize images associated with record with this id.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-p', '--purge',
        action='store_true', dest='purge', default=False,
        help='Purge orphaned images.',
    )
    parser.add_argument(
        '--sizes',
        action='store_true', dest='sizes', default=False,
        help='List all available image sizes and exit.',
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

    quick_exit = False

    if args.fields:
        print('Database image fields:')
        for f in FIELDS:
            print('    {f}'.format(f=f))
        quick_exit = True

    if args.sizes:
        print('Image sizes:')
        for name in SIZES:
            print(name)
        quick_exit = True

    if quick_exit:
        sys.exit(0)

    LOG.info('Started.')

    handler = ImageHandler(
        args.filenames,
        field=args.field,
        record_id=args.id,
        dry_run=args.dry_run,
    )

    if args.purge:
        handler.purge()
    else:
        handler.resize()
        time.sleep(2)           # Allow backgrounded optimizing to complete
        chown()

    LOG.info('Done.')


def chown():
    """Chown of all files."""
    # pylint: disable=protected-access
    uploads_dir = os.path.join(db._adapter.folder, os.pardir, 'uploads')
    args = []
    args.append('chown')
    args.append('-R')
    args.append('http:http')
    args.append(uploads_dir)
    with subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE) as p:
        p_stdout, p_stderr = p.communicate()
    # Generally there should be no output. Log to help troubleshoot.
    if p_stdout:
        LOG.warning('ResizeImg run stdout: {out}'.format(out=p_stdout))
    if p_stderr:
        LOG.error('ResizeImg run stderr: {err}'.format(err=p_stderr))

    if p.returncode:
        raise SyntaxError('chown failed: {err}'.format(
            err=p_stderr or p_stdout))


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
